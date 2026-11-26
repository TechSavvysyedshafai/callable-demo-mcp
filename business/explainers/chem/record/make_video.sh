#!/bin/bash
# record frames -> silent video -> reaction sound from the recorded log -> video with sound.
# Usage: THREE_JS=/path/three.min.js OUT=/path/out [MODE=short] [FPS=30] ./make_video.sh
set -e
cd "$(dirname "$0")"
OUT=${OUT:-$PWD/out}
[ -f "$OUT/rpm.json" ] || node record.js
FPS=${FPS:-60}
ffmpeg -y -loglevel error -framerate $FPS -i "$OUT/frames/f%05d.jpg" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -movflags +faststart "$OUT/chem_silent.mp4"
python3 chem_sound.py "$OUT/rpm.json" "$OUT/chem.wav"
ffmpeg -y -loglevel error -i "$OUT/chem_silent.mp4" -i "$OUT/chem.wav" -c:v copy -c:a aac -b:a 160k -shortest "$OUT/chem_walkthrough.mp4"
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate -show_entries format=duration -of compact "$OUT/chem_walkthrough.mp4"
