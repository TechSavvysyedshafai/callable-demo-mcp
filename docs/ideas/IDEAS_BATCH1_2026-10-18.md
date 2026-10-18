# Idea batch 1: "who is forced to trade?" (written 2026-10-18, BEFORE any test)

Rule: the AI proposes, a fixed test decides. All 10 ideas are tested ONCE on the dev data, with the rules below. No tuning, no variants.
Trials: exactly 10 (one per idea). Bonferroni alpha = 0.05 / 10 = 0.005.

Data: NIFTY daily (2000..dev cutoff), NIFTY 5-minute (2022..dev cutoff), India VIX daily (dev). Hidden holdout NOT touched.
Trading proxy: NIFTY futures, long or short. Cost: 0.10% of notional per round trip (about 24 points; deliberately harsher than the ~15 points measured). Entries/exits only at the stated bar open or close; decide on information known at that time.

Pass rule for each idea (all must hold): (a) mean net return per trade > 0 after cost; (b) block-bootstrap p < 0.005 (one-sided, mean > 0); (c) beats a random-entry null with the same number of trades and holding time (p < 0.005); (d) positive net mean in each half of the dev period; (e) at least 60 trades. Verdict: SURVIVES / REJECT / INCONCLUSIVE (passes a-b only). Also report the same idea with cost 0 so we see if the edge exists before costs.

| # | Forced trader | Rule (fixed) |
|---|---|---|
| 1 | SIP and salary inflows | Long from close of the 2nd-last trading day of a month to close of the 3rd trading day of the next month. |
| 2 | Day traders squaring off | Overnight only: long every close to next open, versus intraday only (open to close). Report both; trial = the overnight leg. |
| 3 | Gap chasers and stop-outs | If open is more than 0.7% away from previous close, trade against the gap from open to close. |
| 4 | Forced sellers (margin calls) | After a close down 2% or more, long next open to next close. |
| 5 | Panic hedgers | After India VIX rises 15% or more in a day, long at that close, exit at close 3 trading days later. |
| 6 | Closing-auction and index funds | 5-min data: if the return from 14:15 to 15:15 is positive, long 15:15 to 15:25 close (negative: short). |
| 7 | Early-morning order flow | 5-min data: first 30-minute return sign; trade the same direction from 09:45 to 15:15. |
| 8 | Pre-holiday risk-takers | Long close of the last trading day before any market holiday (gap of 2+ calendar days beyond weekends) to next open. |
| 9 | Weekend risk reducers | Long Friday close to Monday close. |
| 10 | Weekly-expiry flows | Trade the expiry day (real calendar: Thursday until 2025-08-28, Tuesday from 2025-09-02) open to close, in the direction of the previous day's return. |

Reporting: plain language, answer first, one table, negatives as plainly as positives. Append to research/RESULTS.md. Append the 10 trials to a ledger (research/ideas/ledger_ideas.jsonl).

After the test: ideas that SURVIVE go to a paper-signal recorder (daily, records what the rule would have done; NO re-testing and NO new variants). Ideas that fail are closed.
