import json
from pathlib import Path

STATE_DIR = Path("sources/state")

def load_json(path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except:
            return {}
    return {}

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    merged = {}

    # 遍历所有 cache.json（来自三个 job）
    for f in Path("merged").rglob("cache.json"):
        data = load_json(f)
        for url, info in data.items():
            # 后写入的覆盖旧的（最新检测结果优先）
            merged[url] = info

    # 写回最终 cache.json
    save_json(STATE_DIR / "cache.json", merged)

if __name__ == "__main__":
    main()
