# What we tried, and what it showed (2026-10-18)

Goal set by the owner: roughly triple an FD rate (about 20%/year), steady, not get-rich-quick. Honest benchmark: buy-and-hold NIFTY.
All numbers are on DEV data only; the newest 6 months were kept as a hidden holdout and never read. Details and dates: `research/RESULTS.md`.

| Idea | Verdict | Why |
|---|---|---|
| NIFTY futures scalp (momentum) | FAIL | Costs about 15 index points per round trip; the signal earned about zero before costs |
| NIFTY option-buying scalp, modelled prices | artefact | Black-Scholes prices flattered it; the weekly-expiry weekday also changed over the years |
| Same option scalp, REAL option candles (+/-5 and +/-12 strikes) | FAIL | Negative before costs; fails at every spread assumption tried |
| Daily range-forecast (HAR blend) | REJECT | 6% better than EWMA overall, but 96% of the gain came from 2019-2021 (COVID); slightly worse in the last two years |
| Low-turnover: 200-day trend filter | REJECT | -3.8 pp/yr vs buy-and-hold at 0.25% cost per trade; drawdown benefit not statistically separable |
| Low-turnover: monthly 10-month trend filter | INCONCLUSIVE | Halves the worst drop (-31% vs -60%) for about -2 pp/yr; misses the pre-registered rule |
| Low-turnover: volatility-targeted exposure | REJECT | Worse return in every period; daily resizing costs about 4 pp/yr |

## Numbers worth remembering (NIFTY 50 price index, 2000-2026, cash assumed 6.5%)
- Buy-and-hold: 12.6%/yr (about 13.5-14% with dividends), but a -60% worst drop (2008). That is roughly 2x an FD, not 3x.
- Monthly trend filter: 10.5%/yr with a -31% worst drop. It trades return for smaller crashes; it does not add return.
- Nothing tested comes close to 20%/year. Do not plan on it.

## What this means
1. No tested strategy has an edge after realistic costs. This is an honest, valuable answer, not a failure of the process.
2. The process works: pre-registration, real prices, hidden holdout, independent re-checks and hostile review each caught a flattering result.
3. Active scalping of NIFTY is the hardest corner (costs dominate). Slow strategies lose little to costs but did not beat the index.

## If you continue (pick at most one, written down first)
- Momentum rotation across sectors or stocks, monthly (needs more data; documented in the literature; one pre-registered trial).
- Volatility inputs (open interest, implied vs realised volatility, event days) used for sizing, not direction.
- Record live option quotes for several weeks to measure true spreads before any further option work.
- Or stop: a low-cost index fund is the evidence-based default, and this project is a good learning asset.

Hard limits that stay: no order placement code, no real money without the owner's written approval, never touch the holdout, never put secrets in chat.
