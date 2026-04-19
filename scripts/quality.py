import subprocess
import json
import re
import tempfile
import threading
from pathlib import Path
from PIL import Image
import numpy as np
import cv2

CACHE_FILE = Path(__file__).parent / "cache.json"
cache_lock = threading.Lock()

# ---------------------------
# 加载缓存
# ---------------------------
def load_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except:
            return {}
    return {}

# ---------------------------
# 保存缓存
# ---------------------------
def save_cache(cache):
    with cache_lock:
        CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


cache = load_cache()


def run_silent(cmd, timeout=5):
    """完全屏蔽输出，避免 Windows GBK 崩溃"""
    return subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout
    )


# ---------------------------
# ffprobe: 分辨率 + 码率
# ---------------------------
def probe_stream(url, timeout=5):
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,bit_rate",
            url
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout
        )

        data = json.loads(result.stdout)
        stream = data["streams"][0]

        return True, stream.get("width", 0), stream.get("height", 0), int(stream.get("bit_rate", 0))
    except:
        return False, 0, 0, 0


# ---------------------------
# ffmpeg: 首帧延迟（简化）
# ---------------------------
def measure_first_frame_delay(url, timeout=5):
    try:
        cmd = ["ffmpeg", "-v", "quiet", "-i", url, "-vframes", "1", "-f", "null", "-"]
        run_silent(cmd, timeout=timeout)
        return 1.0
    except:
        return 999


# ---------------------------
# ffmpeg: 截图 + 清晰度检测
# ---------------------------
def snapshot_blur_score(url, timeout=5):
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False).name
        cmd = ["ffmpeg", "-v", "quiet", "-y", "-i", url, "-vframes", "1", tmp]
        run_silent(cmd, timeout=timeout)

        img = Image.open(tmp).convert("L")
        arr = np.array(img)
        return cv2.Laplacian(arr, cv2.CV_64F).var()
    except:
        return 0


# ---------------------------
# 综合评分（带缓存）
# ---------------------------
def quality_score(url):
    # 缓存命中
    if url in cache:
        return cache[url]["score"]

    ok, w, h, bitrate = probe_stream(url)
    delay = measure_first_frame_delay(url)
    blur = snapshot_blur_score(url)

    if not ok:
        score = -999999
    else:
        score = (w * h) / 1000 + bitrate / 10000 + blur - delay * 10

    cache[url] = {
        "width": w,
        "height": h,
        "bitrate": bitrate,
        "delay": delay,
        "blur": blur,
        "score": score
    }
    save_cache(cache)

    return score
