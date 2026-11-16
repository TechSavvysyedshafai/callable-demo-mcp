---
name: shorts-audience
description: Find how Class 11-12 students actually talk about biology and physics help, in their own words, from public YouTube comments on category videos and public reviews of competing courses. Produces business/videos/audience.md and voc.md (verbatim quotes with URLs). Use before writing titles or picking topics, or when the owner asks "what do students struggle with". Adapted from boring-marketing-skills audience-research; respects the owner's no-scrape list.
---

# Shorts audience

Bring back students' exact words, with the URL for each quote. Paraphrase is not evidence.

## Sources (owner's rules apply)
- **Allowed:** public YouTube comments under *other* channels' videos on the same chapter
  (not our own: they are already converted), public reviews of competing courses
  (Udemy, Physics Wallah/Unacademy app-store reviews, Skool), Quora answers, exam-forum threads that are public.
- **Never:** LinkedIn, Facebook, Instagram, Reddit. The owner has ruled these out. Do not
  work around this with a third-party scraper.
- **Credits:** Firecrawl and Exa calls cost credits. Run only after the owner says yes to the
  run and its credit budget; otherwise use free WebSearch/WebFetch only and say the sample is smaller.

## Method
1. Pick 4-6 sources across types: comments (aspiration, confusion), course reviews 2-4 stars
   (judgement), forum threads (pre-exam panic and comparison).
2. Budget per source: at most 5 page reads. Return 8-15 verbatim entries per source:
   `quote | url | date | context | theme (pain/desire/objection/vocabulary) | intensity 1-5`.
3. Bar: 25 quotes across 3 source types. Under the bar, write the files anyway and say so in the header.
4. Synthesis: cluster pains by frequency x intensity; separate table stakes (every channel gets
   "too fast", "too long") from differentiators; harvest repeated exact phrases with counts
   (these become titles); name the dominant emotion with the 2-3 quotes that earn it; list surprises.

## Output
- `business/videos/voc.md`: Pains, Desires, Objections, Vocabulary, each quote with an ID and URL.
- `business/videos/audience.md`: segments (board, class, exam), pain language, where they talk, surprises.
- Chat: the 5 most actionable findings, each with one quote and where it was said, then the one next step.
Never invent a quote. If a source is blocked, report the skip.
