# Explainer kit: voice, captions, music, sound effects, QA

Takes one of our recorded explainers (engine, GPU, F1, or any silent screen recording) and finishes it:
voiceover, word-highlighted captions, a soft music bed that dips under the voice, sound effects on chosen
words, loudness set to -14 LUFS (YouTube level), then 10 automatic checks.

```
python3 make.py examples/f1/script.md     # -> examples/f1/renders/f1_airflow_voiced.mp4
python3 qa.py   examples/f1               # must say 10/10; writes work/qa/contact.jpg
```
Needs: python3 + numpy, ffmpeg (with libass), and `espeak-ng` for the draft voice (`apt-get install espeak-ng`).

## script.md
```
Video: path/to/silent_or_sound.mp4     (relative to the script)
Voice: espeak:en-gb | own:recordings | none
Music: synth:warm | synth:minimal | none
Video sound: 0.35                      (how loud the original engine/wind sound stays)
Captions: on | off
Max duration: 41

## Lines
- @10.4 {whoosh} Now speed up. Downforce grows with speed squared.
```
- `@10.4` = start this line at 10.4 s, so it lands on what the video shows. Without it, the line follows the one before.
- `{whoosh}` before a word = play that sound on that word. Sounds: whoosh, pop, tick, rumble, rise.
- `## Facts` = each claim the script makes, with its source. Check these before publishing.

## Voices (best first)
| Voice | Cost | Quality |
|---|---|---|
| `own:recordings`: your phone recordings `line01.wav`, `line02.wav` ... one per line | free | best, your own voice |
| ElevenLabs (connector is attached) | uses your credits, only with your yes | very good |
| `espeak:en-gb` | free, offline | robotic; for drafts and timing only |

The original project uses Kokoro (a free local voice) and Parakeet (exact word timing). Both download from
Hugging Face, which this cloud machine cannot reach, so they are not used here. Word times inside a line are
estimated from word length; line starts and ends are exact.

## The 10 checks (qa.py)
1 H.264 format · 2 size 1920x1080 / 1080x1920 / 1080x1080 · 3 frame rate · 4 length within the cap
· 5 one audio track · 6 loudness -14 ±1.5 LUFS, peak at most -1 dBTP · 7 no black gaps · 8 no picture frozen 3 s+
· 9 captions not too fast (≤ 22 characters/second), no overlaps, inside the safe band · 10 voice falls inside caption times.
Then look at `work/qa/contact.jpg` yourself (or ask a fresh agent): does any frame look like a slide? Do the first
15 seconds move?

## Credit
Workflow ideas (script rules, word-synced captions, synthesized music and sound cues, QA checks, fresh-eyes review)
come from [petergyang/video-explainer](https://github.com/petergyang/video-explainer), MIT licence,
Copyright (c) 2026 Peter Yang. Its licence text is in `NOTICE`. No code was copied; this is a smaller rewrite
for our own recordings.
