# Biology in 50 seconds (test shorts)

Three silent vertical shorts (720x1280, 24 fps, about 50 s each), made from code. There is no AI video and no voice yet.

- `bio_heart.mp4`: cardiac cycle
- `bio_nephron.mp4`: urine formation
- `bio_mitosis.mp4`: mitosis (PMAT)

Re-render: `node render.js heart.js out_dir 24`, then encode with ffmpeg (see the commit). The captions are timed so that a voiceover can be recorded over them.

Science was checked against standard NCERT Class 11 facts from memory. It was not compared line by line with the book, so a teacher should review it before posting.
Changes from the pasted scripts:
- Cardiac: "at about 72 beats a minute" was added before 0.8 s.
- Nephron: the loop of Henle now shows water leaving the descending limb and salts leaving the ascending limb. The middle volume numbers (about 45 L after the PCT, about 25 L after the loop) are rough and labelled "approx.".
