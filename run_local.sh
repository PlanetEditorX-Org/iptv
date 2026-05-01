#!/bin/bash

set -e

echo "=== IPTV 本地构建开始 ==="

# -----------------------------
# 1. 安装依赖（如果已安装会自动跳过）
# -----------------------------
echo "=== 检查并安装依赖 ==="

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "安装 ffmpeg..."
    sudo apt update
    sudo apt install -y ffmpeg
fi

pip3 install pillow numpy opencv-python-headless --quiet

# -----------------------------
# 2. 选择排序方式（中文）
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
# 6. 合并最终输出（channels_all.m3u / txt / README）
# -----------------------------
echo "=== 合并最终输出 ==="
mkdir -p output
shopt -s nullglob
shopt -s globstar

echo "=== 查找所有 M3U 文件 ==="
find merged -name "channels_*.m3u"

echo "=== 输出每个 M3U 的前 100 行（用于调试） ==="
for f in $(find merged -name "channels_*.m3u"); do
	echo "----- $f -----"
	head -n 100 "$f" || true
	echo
done

echo "=== 合并 TXT ==="
touch output/channels_all.txt

txt_files=( $(find merged -name "channels_*.txt") )

if [ ${#txt_files[@]} -eq 0 ]; then
	echo "⚠️ 没有任何 TXT 文件可合并" >> output/channels_all.txt
else
	for f in "${txt_files[@]}"; do
		echo "合并：$f"
		cat "$f" >> output/channels_all.txt
		echo "" >> output/channels_all.txt
	done
fi

echo "=== 合并 M3U ==="
echo "#EXTM3U" > output/channels_all.m3u

m3u_files=( $(find merged -name "channels_*.m3u") )

if [ ${#m3u_files[@]} -eq 0 ]; then
	echo "⚠️ 没有任何 M3U 文件可合并"
else
	for f in "${m3u_files[@]}"; do
		echo "合并：$f"
		grep -a -h -v "#EXTM3U" "$f" >> output/channels_all.m3u || true
	done
fi
python3 scripts/merge_state_files.py

echo "=== IPTV 本地构建完成 ==="
echo "输出文件位于：output/"
