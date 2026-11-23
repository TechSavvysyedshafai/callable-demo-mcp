#!/bin/bash
set -e; cd "$(dirname "$0")"; mkdir -p seg; F=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
dt(){ echo "drawtext=fontfile=$F:text='$1':fontsize=30:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=14:x=(w-text_w)/2:y=h*0.06:enable='lt(t,5)'"; }
mk(){ ffmpeg -y -loglevel error -framerate 8 -pattern_type glob -i "$2/f*.png" -f lavfi -i anullsrc=r=44100:cl=mono -vf "fps=24,scale=720:1280:flags=lanczos,$(dt "$3")" -shortest -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac seg/$1.mp4; }
card(){ ffmpeg -y -loglevel error -f lavfi -i color=c=0x10131f:s=720x1280:d=$3:r=24 -f lavfi -i anullsrc=r=44100:cl=mono -vf "drawtext=fontfile=$F:text='$1':fontsize=44:fontcolor=white:x=(w-text_w)/2:y=500,drawtext=fontfile=$F:text='$2':fontsize=26:fontcolor=0xbbbbbb:x=(w-text_w)/2:y=600" -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac seg/$4.mp4; }
card "Blender add-on test reel" "5 tools, 5 minutes, all built in code" 5 c0
mk s1 o_gn "1  Geometry Nodes - the Grasshopper of Blender"
mk s2 o_mol "2  Real protein (HIV capsid 1A8O) as nodes"
for a in 0 1 2; do ffmpeg -y -loglevel error -framerate 8 -pattern_type glob -i "o_phys$a/f*.png" -vf "fps=24,scale=720:1280:flags=lanczos,$(dt "3  Rigid-body physics")" -c:v libx264 -crf 20 -pix_fmt yuv420p seg/p$a.mp4; done
ffmpeg -y -loglevel error $(for a in 0 1 2; do echo -i seg/p$a.mp4; done) -f lavfi -i anullsrc=r=44100:cl=mono -filter_complex "concat=n=3:v=1:a=0[v]" -map "[v]" -map 3 -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac seg/s3.mp4
mk s4 o_toon "4  Freestyle toon outlines"
ffmpeg -y -loglevel error -framerate 8 -pattern_type glob -i "o_sound/f*.png" -i reel_audio.wav -vf "fps=24,scale=720:1280:flags=lanczos,$(dt "5  Sound drives the animation")" -shortest -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac seg/s5.mp4
card "Done" "Molecular Nodes could not be installed here" 5 c1
for x in c0 s1 s2 s3 s4 s5 c1; do echo "file seg/$x.mp4"; done > list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i list.txt -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac blender_addons_reel.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 blender_addons_reel.mp4
