# Dadi ki Kahani: story video samples

Done-for-you product test (see the idea evaluation in chat, 26 Nov 2026): Dadi sends voice notes; we return a
60-second illustrated story video, Hindi or Bhojpuri, with word-highlighted captions and an English line.

`pyasa_kauwa/` The Thirsty Crow (public-domain folk tale). 1080x1920, 58 s, QA 10/10.
Voice is the espeak Hindi robot placeholder; swap in Dadi's recordings with `Voice: own:recordings`
(files `recordings/line01.wav` ... one per line) and re-run.

Build (needs Node 22, Python 3, ffmpeg, fonts-noto-core):
```
cd pyasa_kauwa && npm install
python3 ../../explainer_kit/make.py script.md --plan        # time the voice
npx remotion render src/index.ts Story out/silent.mp4 --browser-executable=/opt/pw-browsers/chromium
python3 ../../explainer_kit/make.py script.md && python3 ../../explainer_kit/qa.py .
```
Animation: Remotion (free for individuals and companies of up to 3 people; larger companies need a licence).

## Characters (added 26 Nov 2026)
`pyasa_kauwa/src/Dadi.tsx` is a reusable storyteller: Dadi walks in with her stick, fans herself with a pankha,
watches the story and raises a finger for the lesson. Props: start/end x, walk start time, fan and raise windows.
Her walk is solved by `src/lineart/gait.ts` and her limbs use the open-stroke ink style, both from
JDhruv14/line-art-animation (MIT, licence in `src/lineart/LICENSE`); `pure.ts` ports two of its drawing helpers
so they work inside Remotion. Reuse her in any new story by importing `Dadi` and placing her in the scene.
