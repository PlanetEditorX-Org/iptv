#!/bin/bash

set -e

echo "=== IPTV 本地构建开始 ==="

# -----------------------------
# 0. 自动创建虚拟环境（如果不存在）
# -----------------------------
if [ ! -d "venv" ]; then
    echo "=== 创建虚拟环境 venv ==="
    python3 -m venv venv
fi

echo "=== 激活虚拟环境 ==="
source venv/bin/activate

# -----------------------------
# 1. 安装依赖（仅安装到 venv，不污染系统）
# -----------------------------
echo "=== 安装依赖（虚拟环境） ==="
pip install --upgrade pip
pip install pillow numpy opencv-python-headless requests

# -----------------------------
# 2. 排序方式
# -----------------------------
SORT_MODE="高质量 → 本地源"
echo "使用排序方式：$SORT_MODE"

# -----------------------------
# 3. 构建 CCTV
# -----------------------------
echo "=== 构建 CCTV ==="
python3 scripts/build_job.py cctv "$SORT_MODE"

# -----------------------------
# 4. 构建 卫视
# -----------------------------
echo "=== 构建 卫视 ==="
python3 scripts/build_job.py satellite "$SORT_MODE"

# -----------------------------
# 5. 合并 cache.json
# -----------------------------
echo "=== 合并 cache.json ==="
python3 scripts/merge_cache.py

# -----------------------------
# 6. 合并最终输出
# -----------------------------
echo "=== 合并最终输出 ==="

mkdir -p output

echo "=== 合并 TXT ==="
echo "#EXTM3U" > output/channels_all.txt
for f in output/channels_*.txt; do
    echo "合并：$f"
    cat "$f" >> output/channels_all.txt
    echo "" >> output/channels_all.txt
done

echo "=== 合并 M3U ==="
echo "#EXTM3U" > output/channels_all.m3u
for f in output/channels_*.m3u; do
    echo "合并：$f"
    grep -a -h -v "#EXTM3U" "$f" >> output/channels_all.m3u
done

# -----------------------------
# 7. 生成 README
# -----------------------------
python3 scripts/merge_state_files.py

echo "=== IPTV 本地构建完成 ==="
echo "输出文件位于：output/"
