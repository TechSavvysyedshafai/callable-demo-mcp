#!/bin/bash
# usage: make.sh name scene3d.py  -> renders Blender frames on twos, overlay, composite MP4
set -e; cd "$(dirname "$0")"; N=$1; PY=$2
node render.js $N.js st_$N 24 "" state >/dev/null
node render.js $N.js ov_$N 24 "" overlay >/dev/null
LAST=$(( $(ls ov_$N | wc -l) - 1 ))
mkdir -p b_$N; STEP=2 ../blender/venv/bin/python $PY -- st_$N/state.json $PWD/b_$N 0 $LAST 75 12 > b_$N.log 2>&1
ffmpeg -y -loglevel error -framerate 12 -pattern_type glob -i "b_$N/f*.png" -framerate 24 -i ov_$N/f%04d.png \
 -filter_complex "[0]fps=24,scale=720:1280:flags=lanczos[b];[b][1]overlay=shortest=1,fade=t=in:st=0:d=0.3" -c:v libx264 -crf 20 -pix_fmt yuv420p -movflags +faststart bio3d_$N.mp4
grep sec/frame b_$N.log; ffprobe -v error -show_entries format=duration -of csv=p=0 bio3d_$N.mp4
