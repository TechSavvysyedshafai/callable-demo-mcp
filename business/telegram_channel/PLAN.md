# Fifty Second Syllabus: Telegram channel run by Claude

Goal: grow a free Class 11-12 science audience on Telegram, using the videos we already made,
then later sell paid notes, doubt sessions or AI Helper Patna services to that audience.

## How it runs (autonomous, inside safe limits)
- One post a day at 18:47 India time (students' evening), from the pre-written queue in `queue.json`.
- Each post: one short video (under 50 MB) + 3 plain lines + one quiz question.
  The next day's post opens with yesterday's answer.
- Claude posts with the bot @AIHelperPatna_bot, which is an admin of the channel.
- Progress is kept in `state.json` (next post number), committed to the repo after each post.
- Every Sunday Claude sends Syed a short Telegram note: what was posted, what is next, anything that failed.

## Hard rules
1. Post only items from `queue.json`. New items are added only after Syed reads them.
2. No ads, no paid promotion, no links to anything paid, no personal messages to channel members.
3. Facts come only from the video's own script; quiz answers are textbook facts.
4. If a post fails twice in a row, stop and tell Syed.
5. Costs nothing: no Firecrawl, no ElevenLabs, no paid tools.

## Limits (honest)
- The bot can post, but in this cloud session it cannot read replies or comments.
- Telegram's bot tools here cannot read the member count; Syed checks it in the app.
- Posting runs only while this Claude session exists; if the session ends, the schedule stops.

## Money later (judgment)
- At about 500 members: free weekly live doubt session to build trust.
- At about 2,000 members: paid chapter notes or a Rs 99-199 monthly "daily practice" group.
- Chance of reaching 2,000 members in 6 months with daily posts alone: about 15-25% (judgment).
  Posting the same videos on YouTube Shorts and Instagram and linking the channel raises it.
