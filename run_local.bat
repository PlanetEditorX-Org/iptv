@echo off
chcp 65001 >nul

echo === IPTV Local Build Start ===

REM Install Python dependencies
pip install pillow numpy opencv-python-headless >nul

REM Sort mode
set SORT_MODE=high_local
echo Using sort mode: %SORT_MODE%

REM Build CCTV
echo === Building CCTV ===
python scripts\build_job.py cctv "%SORT_MODE%"

REM Build Satellite
echo === Building Satellite ===
python scripts\build_job.py satellite "%SORT_MODE%"

REM Merge cache
echo === Merging cache.json ===
python scripts\merge_cache.py

REM Merge outputs (TXT + M3U)
echo === Merging outputs ===

if not exist output mkdir output

REM Merge TXT
echo #EXTM3U > output\channels_all.txt
for %%f in (output\channels_*.txt) do (
    echo Merging TXT: %%f
    type "%%f" >> output\channels_all.txt
    echo. >> output\channels_all.txt
)

REM Merge M3U
echo #EXTM3U > output\channels_all.m3u
for %%f in (output\channels_*.m3u) do (
    echo Merging M3U: %%f
    findstr /V "#EXTM3U" "%%f" >> output\channels_all.m3u
)

REM Merge state files
echo === Merging state files ===
python scripts\merge_state_files.py

echo === IPTV Local Build Finished ===
echo Output files are in: output\
pause
