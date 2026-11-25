#!/bin/bash
# Full pipeline: record frames -> silent 60 fps 1080p video -> engine sound from rpm log -> final video with sound.
# Usage: THREE_JS=/path/three.min.js OUT=/path/out ./make_video.sh
set -e
cd "$(dirname "$0")"
OUT=${OUT:-$PWD/out}
[ -f "$OUT/rpm.json" ] || node record.js
ffmpeg -y -loglevel error -framerate 60 -i "$OUT/frames/f%05d.jpg" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -movflags +faststart "$OUT/engine_walkthrough_silent.mp4"
python3 engine_sound.py "$OUT/rpm.json" "$OUT/engine.wav"
ffmpeg -y -loglevel error -i "$OUT/engine_walkthrough_silent.mp4" -i "$OUT/engine.wav" -c:v copy -c:a aac -b:a 160k -shortest "$OUT/engine_walkthrough.mp4"
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate -show_entries format=duration -of compact "$OUT/engine_walkthrough.mp4"
