---
name: explainer-video
description: Finish a recorded explainer (engine/GPU/F1 pages or any screen recording) into a publishable video with voiceover, word-highlighted captions, music bed, sound effects and 10 automatic QA checks. Use when the owner asks to add voice, captions or music to a video, or to make an explainer short. Ideas adapted from petergyang/video-explainer (MIT).
---

# Explainer video

Kit: `business/videos/explainer_kit/` (read its README for script.md syntax).

1. **Script (60-75 s, max 120 s; ~2.5 spoken words per second of video).** Open with a question or number in the
   first 3 seconds. Follow one example from start to end and answer the opening question at the end. Plain English, short
   sentences, active verbs. No hype words, no unexplained acronyms. Time each line with `@seconds` to what the
   video shows at that moment (read the recorder's timeline in `record/record.js`).
2. **Fact check.** List every claim under `## Facts` with its source. Say what is verified and what is assumed.
   Rules that change (sport rules, prices, limits) need a source checked today.
3. **Voice.** Ask which voice: his own recordings (best, free), ElevenLabs (credits; only on his yes), or the espeak
   draft voice. Never spend credits without a yes.
4. **Build and check.** `python3 make.py <project>/script.md`, then `python3 qa.py <project>`. Fix every failure until it
   reaches 10/10.
5. **Fresh eyes.** Look at `work/qa/contact.jpg` and `opening.jpg`. Do the captions hide a control or a number the voice
   talks about? Does any stretch look like a slide? Does the opening move? Fix it, then rebuild.
6. **Deliver.** Commit the render, report its length, loudness and QA score, and offer the `shorts-publish` pack.
