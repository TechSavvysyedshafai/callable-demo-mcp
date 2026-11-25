#!/bin/bash
# record frames -> silent 60 fps video -> wind rush / vortex sound from recorded airspeed and DRS -> final video.
# Usage: THREE_JS=/path/three.min.js OUT=/path/out [MODE=short] ./make_video.sh
set -e
cd "$(dirname "$0")"
OUT=${OUT:-$PWD/out}
[ -f "$OUT/rpm.json" ] || node record.js
ffmpeg -y -loglevel error -framerate 60 -i "$OUT/frames/f%05d.jpg" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -movflags +faststart "$OUT/f1_walkthrough_silent.mp4"
python3 wind_sound.py "$OUT/rpm.json" "$OUT/wind.wav"
ffmpeg -y -loglevel error -i "$OUT/f1_walkthrough_silent.mp4" -i "$OUT/wind.wav" -c:v copy -c:a aac -b:a 160k -shortest "$OUT/f1_walkthrough.mp4"
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate -show_entries format=duration -of compact "$OUT/f1_walkthrough.mp4"
