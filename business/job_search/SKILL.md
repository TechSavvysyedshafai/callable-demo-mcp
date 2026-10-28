---
name: job-search
description: Find remote jobs, score how well the user really fits, write a tailored resume and cover letter per job, and keep a tracker. Honest about gaps. Never submits applications.
---

# Job search assistant (honest edition)

Owner profile: see `profile.json`. Tracker: `job_tracker.csv`. Scoring: `score.py`.

## Rules
1. Say what happened. If a site blocked a search or a link failed, say so in the report.
2. Never invent experience, skills, numbers or dates. A missing requirement is listed as a gap.
3. Never submit an application, create an account or handle logins, captchas or OTPs. The user clicks Apply.
4. Do not scrape LinkedIn, Facebook or Instagram. Use public job pages and company career pages only.
5. Read Gmail only when asked, and only for replies from companies in the tracker.
6. Scheduled runs need the user's yes first, and the report must say they are scheduled runs.

## Steps for `search`
1. Read `profile.json`. Ask only for what is missing.
2. Search public pages (Indeed, Foundit, Glassdoor, company career pages, Workable, Ashby, a16z board).
3. Open every posting that looks relevant. Drop it if the page does not load or the role is closed. Note the posting date.
4. Score each posting with `python3 score.py` (rubric below). Write the reasons in plain words.
5. For roles at 40% or more, write a tailored resume and cover letter from the real resume only.
6. Add one row per role to `job_tracker.csv` (status `Found`).
7. Report: table of role, company, posting age, score, gaps, apply link. Then the real chance of an interview, in a range.

## Fit rubric (weights)
skills overlap 3, years of experience 2, domain 2, seniority 2, project relevance 1, education 1. Each input is 0 to 1.
If a requirement marked "required" is missing, the total is capped at 45%. The score is not the chance of an interview.

## Honest chance of an interview
Fit 65%+ and no hard gap: 20-35%. Fit 40-64% or one hard gap: 5-15%. Below 40%: under 5%.

## Status flow
Found, Ready to apply, Applied, Acknowledged, Assessment, Interview, Offer, Rejected, Ghosted (21+ days).
Follow-up reminder 7 days after Applied.
