---
name: listing-review
description: Use when asked to review, value or write a buyer-side report on an online business listing (Flippa and similar). Public data only, estimates labelled, scenarios and a simulation, plain verdict. Never contacts sellers or buyers without the owner's yes.
---

# Listing review (buyer-side sample report)

Template and worked example: `business/flippa_report/build.py` (run `python3 -I build.py`, it writes `report.html` and `results.json`). Copy it, change the listing facts at the top, rebuild, publish as a private Artifact.

## Rules
1. **Public pages only.** Do not log in, scrape behind a login, or break the platform's terms. If a price or figure is hidden, say so and mark any estimate as an estimate.
2. **Verified vs derived vs assumed.** Every number carries one of these labels. Listing figures are verified only as "copied from the page". Revenue, costs, payback, price estimates are derived. Scenarios, simulation inputs, risk percentages, scores and the bid range are assumed, and say so.
3. **Check the method.** Reproduce the asking prices of at least two comparable listings (profit x 12 x multiple) before trusting the same method on a hidden price.
4. **Flag conflicts** inside the listing (for example an age field that disagrees with the text). Do not smooth them over.
5. **Concentration first.** Revenue per 1,000 views far above ad rates means few paying partners. Ask for revenue by partner.
6. **No advice, no guarantees.** Give ranges, state what is missing, add the "not advice, not affiliated" line.
7. **Outward actions need an explicit yes.** Sending a report to anyone other than the owner, or contacting a buyer or seller, is not done unprompted. Sending to the owner's own address as a test is fine when asked.
8. **Credits.** Search and scrape cost credits. Say what was spent. Stop when the page shows a login wall instead of retrying.

## Report sections (keep this order)
Summary and verdict; listing facts with status pills; valuation vs comparisons (sold, asking, benchmark labelled apart); unit economics; payback scenarios; Monte Carlo with inputs listed; risk register with chances labelled as judgment; ten questions for the seller; score and verdict; sources, verified vs assumed, limits.

## Style
Answer first, plain words, percentages for chances, no hype. Match `research-reporting` for tone. Charts follow the `dataviz` skill (validated palette, direct labels, table fallback). One look at the rendered page before publishing.
