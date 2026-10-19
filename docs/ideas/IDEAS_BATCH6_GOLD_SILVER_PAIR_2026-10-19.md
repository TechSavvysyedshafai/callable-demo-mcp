# Batch 6: gold vs silver ratio pair trade (pre-registered 2026-10-19, BEFORE any test)

Idea: gold and silver usually move together. When the gold-to-silver price ratio stretches far from its recent normal, bet it snaps back: buy the cheap metal, sell the expensive one.

Data: daily closes of the NSE ETFs GOLDBEES and SILVERBEES (NSE_EQ), via the existing Upstox adapter (research/upstox/upstox_api.py; find the instrument keys through the Upstox instrument list or the search API; never print or save the token). Use only data up to the dev cutoff 2026-04-16 (holdout not touched). SILVERBEES listed around 2022 (unverified) so the sample is about four years: few trades, low power. Index of liquidity: ETFs are the PROXY for the metals; the tradable short leg would be MCX futures, for which we have no history. Assumption stated: ETF returns approximate futures returns; futures carry/roll and ETF premiums are not modelled.

## Rule (fixed; ONE trial, trial 16 overall, alpha = 0.05 / 16 = 0.003125)
- r_t = ln(GOLDBEES close / SILVERBEES close). Z_t = (r_t - mean of r over the previous 60 trading days) / std of r over the previous 60 trading days (rolling window of 60 days that ENDS at t, includes t; decisions use close of day t only).
- Signal decided at the close of day t, trade at the NEXT trading day's open.
- If Z >= +2.0: gold is expensive relative to silver: sell gold, buy silver. If Z <= -2.0: buy gold, sell silver. Equal rupee notional on both legs at entry. One pair position at a time.
- Exit at the next day's open after the first close with |Z| <= 0.5, OR after 20 trading days (time stop), OR at the next open after |Z| >= 4.0 (stop). Whichever comes first.
- P&L per trade = (return of the long leg - return of the short leg) over the holding period, entry open to exit open.
- Cost: 0.10% of notional per leg per round trip, so 0.20% per pair trade (harsh, covers spread, brokerage, STT/CTT, slippage). A financing/borrow drag of 0.02% per day held on the short leg (assumption; unverified).
- Pass (all): trades >= 15; mean net per trade > 0; one-sided block bootstrap (blocks of 3 trades, 10,000 resamples) p < 0.003125; positive mean net in each half of the sample (split at the calendar midpoint); beats a random-date null (same number of trades, same holding days, same long/short mix, 10,000 draws) with p < 0.003125. If trades < 15 the verdict is INCONCLUSIVE (too few to judge) whatever the mean.
- Information only, NOT trials: lookback 40 and 90 days, entry thresholds 1.5 and 2.5 (so the owner can see plateau vs spike), zero-cost result, and each half separately.
- No variants chosen after seeing results. Skipped days (missing candles, halts) counted and reported. Do NOT append to research/ideas/loop/ledger_loop.jsonl: the project manager appends the trial after merging. Write trial id B6-01 and its numbers in your results JSON.
