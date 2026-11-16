---
name: shorts-publish
description: Turn one finished 50-second short (biology or physics series) into its publishing pack - title, description, hashtags, pinned comment, community post and one X post - using only facts from the video's own script. Use after a short is rendered, or when the owner asks for titles, descriptions, hooks or a posting plan. Adapted from the open MIT boring-marketing-skills (social-content, content-atomizer, direct-response-copy) for a YouTube Shorts study channel.
---

# Shorts publish

One finished pack per short. Everything in it is written from the script captions in the
scene file (`setSegments([...])`) and the facts already in the repo. Nothing is invented.

## Inputs
- The scene file (`business/videos/*/<name>.js`): the header line gives series and class,
  the captions give every fact the pack may use.
- `business/videos/publish/channel.md` if it exists (channel name, standing hashtags, banned words).
- `business/videos/publish/performance.md` if it exists (what worked; it overrides the defaults below).

## Rules (the claim gate)
1. **Only facts in the script.** A number, name or formula that is not in the captions does
   not go in the title, description or comment. Chapter names may be added only when marked
   `[verify against current NCERT edition]`.
2. **Plain first line.** The title and the first line of the description say what the
   viewer learns, the way a good teacher would say it. No "You won't believe", no emoji-led
   openers, no "Let that sink in", no "game-changer", no fake urgency.
3. **Something to save.** The pinned comment carries the one line a student would screenshot:
   the mnemonic, the order, or the formula. Not a question alone.
4. **Match the video.** Title length under 60 characters so it is not cut on a phone;
   wording matches the caption wording (if the video says "about 72 beats", the title does not say "72 beats").
5. **One finished pack**, not five drafts. Offer the runner-up title in one line.
6. **Never post automatically.** The pack is files; the owner pastes. No scheduling tools.

## The pack (one file per short: `business/videos/publish/<name>.md`)
```
# <Series> · <Topic>
Video: <path>   Class: <11|12>   Chapter: <NCERT chapter name> [verify against current NCERT edition]

## Title (chosen)
<under 60 chars, plain, specific>
Runner-up: <one line>

## Description
<line 1: the hook question or the fact, in the script's words>
<line 2: what the video covers, in order, 1 sentence>
<line 3: "Class 11 Biology · <chapter>. Part of <Series>.">
<blank line>
<3-5 hashtags>

## Pinned comment
<the save line: mnemonic / order / formula>  <one question students can answer in a word>

## Community post (text, day of upload)
<2-3 lines: the hook, the save line, "new short is up">

## X post (text only, link in the first reply)
<2-4 lines, stands without the link>

## Verify before posting
<at most one item, or "nothing">
```

## Cadence
- Post 3 shorts a week at most, same days each week, at a fixed hour the owner chooses.
- Reply to every comment in the first hour after upload.
- After 2 weeks of uploads, read YouTube Studio numbers (views, average view duration,
  swipe-away rate, subscribers per video) into `performance.md`: what to keep, what to cut.
  Numbers beat opinions; this file then overrides the defaults above.

## Banned in any pack
unlock, unleash, supercharge, game-changer, delve, "in today's fast-paced world",
"let that sink in", "here's the thing", "agree?", countdown urgency, claims of ranks or results.
