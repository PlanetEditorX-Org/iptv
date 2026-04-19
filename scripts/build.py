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
CHANNEL_LIST_FILE = SOURCES_DIR / "channel_list.txt"


# ============================
# 读取上游 LIVE_URLS
# ============================
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


# ============================
# 读取频道白名单
# ============================
def load_channel_whitelist():
    whitelist = set()
    if CHANNEL_LIST_FILE.exists():
        with CHANNEL_LIST_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                name = line.strip()
                if name:
                    whitelist.add(normalize_name(name))
    return whitelist


# ============================
# 下载上游内容
# ============================
def fetch_text(url, timeout=8):
    print(f"[fetch] {url}")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding
    return r.text


# ============================
# 频道名规范化
# ============================
def normalize_name(name: str) -> str:
    name = name.strip()

    # CCTV 系列
    m = re.match(r"CCTV[- ]?0?(\d+)", name.upper())
    if m:
        return f"CCTV{m.group(1)}"

    # CETV 系列
    m = re.match(r"CETV[- ]?0?(\d+)", name.upper())
    if m:
        return f"CETV{m.group(1)}"

    # 卫视（去掉乱码）
    name = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]+", "", name)

    return name


# ============================
# URL 过滤规则
# ============================
def is_good_url(u: str) -> bool:
    u = u.strip()
    if not u.startswith("http"):
        return False
    if u.endswith("$"):
        return False
    bad_keywords = ["udp/", "rtp/", "://239.", "://224."]
    if any(k in u for k in bad_keywords):
        return False
    return True


# ============================
# 添加频道源
# ============================
def add_channel(channels, name, url):
    name = normalize_name(name)
    url = url.strip()
    if not name or not url:
        return
    if url not in channels[name]:
        channels[name].append(url)


# ============================
# 解析 txt 格式
# ============================
def parse_txt_like(content, channels):
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if ",http" in line:
            name, url = line.split(",", 1)
        elif "#" in line and "http" in line:
            name, url = line.split("#", 1)
        else:
            continue
        add_channel(channels, name, url)


# ============================
# 解析 m3u 格式
# ============================
def parse_m3u(content, channels):
    last_name = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            if "," in line:
                last_name = line.split(",", 1)[1].strip()
        elif line and not line.startswith("#") and last_name:
            add_channel(channels, last_name, line)
            last_name = None


# ============================
# 解析 TVBox JSON
# ============================
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


# ============================
# 自动识别格式
# ============================
def detect_and_parse(content, channels):
    text = content.lstrip()
    if text.startswith("{") and '"lives"' in text:
        parse_tvbox_json(text, channels)
    elif "#EXTM3U" in text or "#EXTINF" in text:
        parse_m3u(text, channels)
    else:
        parse_txt_like(text, channels)

# ============================
# 节目排序
# ============================
def channel_sort_key(name: str):
    """
    让 CCTV1, CCTV2, ... CCTV10 按数字顺序排，
    其他频道正常字典序。
    """
    m = re.match(r"(CCTV|CETV)(\d+)$", name.upper())
    if m:
        prefix = m.group(1)
        num = int(m.group(2))
        # 让 CCTV 系列排在最前，CETV 其次，其他频道再后
        order_prefix = {"CCTV": 0, "CETV": 1}.get(prefix, 2)
        return (order_prefix, num, "")
    # 非数字频道：放在后面，按名字排
    return (3, 0, name)

# ============================
# 输出酷9可用 txt
# ============================
def build_output_txt(channels, whitelist):
    lines = []
    lines.append("央视频道,#genre#")

    for name in sorted(channels.keys(), key=channel_sort_key):
        if name not in whitelist:
            continue

        urls = [u for u in channels[name] if is_good_url(u)]
        if not urls:
            continue

        for url in urls:
            lines.append(f"{name},{url}")
        lines.append("")
    return "\n".join(lines)


# ============================
# 主流程
# ============================
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    channels = defaultdict(list)
    whitelist = load_channel_whitelist()
    live_sources = load_live_urls()

    for url, label in live_sources:
        try:
            content = fetch_text(url)
            detect_and_parse(content, channels)
        except Exception as e:
            print(f"[error] {url} -> {e}")

    out_txt = build_output_txt(channels, whitelist)
    out_file = OUTPUT_DIR / "ku9_live.txt"
    out_file.write_text(out_txt, encoding="utf-8")

    print(f"[done] wrote {out_file}")


if __name__ == "__main__":
    main()
