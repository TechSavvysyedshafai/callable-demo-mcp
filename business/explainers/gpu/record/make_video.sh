#!/bin/bash
# record frames -> silent 60 fps video -> GPU hum / coil whine from the recorded utilisation and clock -> final video.
# Usage: THREE_JS=/path/three.min.js OUT=/path/out [MODE=short] ./make_video.sh
set -e
cd "$(dirname "$0")"
OUT=${OUT:-$PWD/out}
[ -f "$OUT/rpm.json" ] || node record.js
ffmpeg -y -loglevel error -framerate 60 -i "$OUT/frames/f%05d.jpg" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -movflags +faststart "$OUT/gpu_walkthrough_silent.mp4"
python3 gpu_sound.py "$OUT/rpm.json" "$OUT/gpu.wav"
ffmpeg -y -loglevel error -i "$OUT/gpu_walkthrough_silent.mp4" -i "$OUT/gpu.wav" -c:v copy -c:a aac -b:a 160k -shortest "$OUT/gpu_walkthrough.mp4"
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate -show_entries format=duration -of compact "$OUT/gpu_walkthrough.mp4"
