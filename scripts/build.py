#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT / "sources"
OUTPUT_DIR = ROOT / "output"

LIVE_URLS_FILE = SOURCES_DIR / "live_urls.txt"

def load_live_urls():
    items = []
    with LIVE_URLS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "$" in line:
                url, name = line.split("$", 1)
            else:
                url, name = line, ""
            items.append((url.strip(), name.strip()))
    return items

def fetch_text(url, timeout=8):
    print(f"[fetch] {url}")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    # 尽量用正确编码
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding
    return r.text

def normalize_name(name: str) -> str:
    name = name.strip()
    # CCTV-01 / CCTV1瓒呮竻 / CCTV-1 -> CCTV1
    m = re.match(r"CCTV[- ]?0?(\d+)", name.upper())
    if m:
        return f"CCTV{m.group(1)}"
    # CETV-01 -> CETV1
    m = re.match(r"CETV[- ]?0?(\d+)", name.upper())
    if m:
        return f"CETV{m.group(1)}"
    # 简单去掉一些花字（楂樼爜、瓒呮竻之类）
    name = re.sub(r"[楂樼爜瓒呮竻高清超清HD4K ]+", "", name)
    return name

def add_channel(channels, name, url):
    name = normalize_name(name)
    url = url.strip()
    if not name or not url:
        return
    if url not in channels[name]:
        channels[name].append(url)

def parse_txt_like(content, channels):
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        # 常见格式：名称,URL
        if ",http" in line:
            name, url = line.split(",", 1)
        elif "#" in line and "http" in line:
            # 名称#URL
            name, url = line.split("#", 1)
        else:
            continue
        add_channel(channels, name, url)

def parse_m3u(content, channels):
    last_name = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            # 取逗号后面的显示名
            if "," in line:
                last_name = line.split(",", 1)[1].strip()
        elif line and not line.startswith("#") and last_name:
            url = line
            add_channel(channels, last_name, url)
            last_name = None

def parse_tvbox_json(content, channels):
    try:
        data = json.loads(content)
    except Exception:
        return
    lives = data.get("lives") or []
    for live in lives:
        for ch in live.get("channels", []):
            name = ch.get("name")
            urls = ch.get("urls") or []
            for url in urls:
                add_channel(channels, name, url)

def detect_and_parse(content, channels):
    text = content.lstrip()
    if text.startswith("{") and '"lives"' in text:
        parse_tvbox_json(text, channels)
    elif "#EXTM3U" in text or "#EXTINF" in text:
        parse_m3u(text, channels)
    else:
        parse_txt_like(text, channels)

def build_output_txt(channels):
    lines = []
    lines.append("央视频道,#genre#")
    for name in sorted(channels.keys()):
        urls = channels[name]
        # 简单过滤一下明显的垃圾
        urls = [u for u in urls if u.startswith("http")]
        if not urls:
            continue
        for url in urls:
            lines.append(f"{name},{url}")
        lines.append("")  # 频道之间空一行
    return "\n".join(lines)

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    channels = defaultdict(list)

    live_sources = load_live_urls()
    for url, label in live_sources:
        try:
            content = fetch_text(url)
            detect_and_parse(content, channels)
        except Exception as e:
            print(f"[error] {url} -> {e}")

    out_txt = build_output_txt(channels)
    out_file = OUTPUT_DIR / "ku9_live.txt"
    out_file.write_text(out_txt, encoding="utf-8")
    print(f"[done] wrote {out_file}")

if __name__ == "__main__":
    main()
