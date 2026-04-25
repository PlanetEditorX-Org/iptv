import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import re

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
STATE_DIR = ROOT / "sources" / "state"

M3U_FILE = OUTPUT_DIR / "channels_all.m3u"
README_FILE = ROOT / "README.md"

RAW_FILES = [
    STATE_DIR / "raw_results_cctv.json",
    STATE_DIR / "raw_results_satellite.json",
    STATE_DIR / "raw_results_entertainment.json",
]

UPSTREAM_BLOCKLIST_FILE = STATE_DIR / "upstream_blocklist.json"

def load_json(path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def merge_raw():
    all_raw = {}
    for f in RAW_FILES:
        if not f.exists():
            continue
        data = load_json(f)
        for url, info in data.items():
            all_raw[url] = info
    return all_raw

def parse_m3u():
    channels = {}
    last_name = None
    for line in M3U_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            if "," in line:
                last_name = line.split(",", 1)[1].strip()
        elif line and not line.startswith("#") and last_name:
            channels.setdefault(last_name, []).append(line)
            last_name = None
    return channels

def channel_sort_key(name: str):
    m = re.match(r"(CCTV|CETV)(\d+)", name)
    if m:
        return (m.group(1), int(m.group(2)))
    return ("ZZZ", name)

def get_channel_type(name: str) -> str:
    if name.startswith("CCTV"):
        return "tv"
    if name.endswith("卫视"):
        return "tv"
    return "entertainment"

def build_readme_from_m3u(channels, raw, upstream_blocklist):
    html = []
    html.append("# IPTV 质量报表\n")

    cst = timezone(timedelta(hours=8))
    build_time = datetime.now(cst).strftime("%Y-%m-%d %H:%M:%S")
    html.append(f"⏱ **构建时间：{build_time} (CST)**\n\n")

    report = {}

    for name, urls in channels.items():
        total = len(urls)
        usable = 0
        best_score = -1
        best_res = "N/A"

        for url in urls:
            info = raw.get(url)
            if not info:
                continue
            score = info.get("score", 0)
            if score > 0:
                usable += 1
            if score > best_score:
                best_score = score
                w = info.get("width", 0)
                h = info.get("height", 0)
                best_res = f"{w}x{h}" if w and h else "N/A"

        removed = usable == 0

        report[name] = {
            "total": total,
            "usable": usable,
            "removed": removed,
            "best_res": best_res,
            "best_score": round(best_score, 1) if best_score >= 0 else 0,
            "type": get_channel_type(name),
        }

    total_channels = len(report)
    removed_channels = sum(1 for x in report.values() if x["removed"])
    kept_channels = total_channels - removed_channels
    total_usable = sum(x["usable"] for x in report.values())

    html.append("## 📊 总览统计\n")
    html.append(f"- **总频道数：** {total_channels}")
    html.append(f"- **保留频道数：** {kept_channels}")
    html.append(f"- **已删除频道数：** {removed_channels}")
    html.append(f"- **总可用源数：** {total_usable}\n\n")

    # 电视频道
    html.append("## 📺 电视频道\n\n<table>")
    html.append("<tr><th>频道</th><th>可用源</th><th>最佳分辨率</th><th>最高得分</th><th>状态</th></tr>")

    tv_items = [(name, info) for name, info in report.items() if info["type"] == "tv"]
    for name, info in sorted(tv_items, key=lambda x: (x[1]["removed"], channel_sort_key(x[0]))):
        status = '<span style="color:red">已删除</span>' if info["removed"] else '<span style="color:green">保留</span>'
        html.append(
            f"<tr>"
            f"<td>{name}</td>"
            f"<td>{info['usable']}</td>"
            f"<td>{info['best_res']}</td>"
            f"<td>{info['best_score']}</td>"
            f"<td>{status}</td>"
            f"</tr>"
        )
    html.append("</table>\n")

    # 媒体频道
    html.append("## 📡 媒体频道\n\n<table>")
    html.append("<tr><th>频道</th><th>可用源/总源</th><th>最佳分辨率</th><th>最高得分</th><th>状态</th></tr>")

    ent_items = [(name, info) for name, info in report.items() if info["type"] == "entertainment"]
    for name, info in sorted(ent_items, key=lambda x: (x[1]["removed"], x[0])):
        status = '<span style="color:red">已删除</span>' if info["removed"] else '<span style="color:green">保留</span>'
        html.append(
            f"<tr>"
            f"<td>{name}</td>"
            f"<td>{info['usable']} / {info['total']}</td>"
            f"<td>{info['best_res']}</td>"
            f"<td>{info['best_score']}</td>"
            f"<td>{status}</td>"
            f"</tr>"
        )
    html.append("</table>\n")

    README_FILE.write_text("\n".join(html), encoding="utf-8")

def main():
    print("=== 读取最终 M3U ===")
    channels = parse_m3u()
    print(f"  频道数：{len(channels)}")

    print("=== 合并 raw_results_* ===")
    raw = merge_raw()
    print(f"  URL 记录数：{len(raw)}")

    upstream_blocklist = load_json(UPSTREAM_BLOCKLIST_FILE)

    print("=== 生成 README.md ===")
    build_readme_from_m3u(channels, raw, upstream_blocklist)
    print("=== 完成 ===")

if __name__ == "__main__":
    main()
