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
| Weekly NIFTY iron condor, selling, REAL expired-option prices (80 weeks) | REJECT | Premium collected ~54.5 pts, paid out ~60.4 pts, so it loses even before fees (-Rs437/wk/lot). After fees -Rs640/wk; a 2x-credit stop cuts the loss to -Rs460/wk but stays negative. Short strike breached 48% of weeks. 80 weeks cannot prove the true mean is below zero, and cannot show crash risk |

## Numbers worth remembering (NIFTY 50 price index, 2000-2026, cash assumed 6.5%)
- Buy-and-hold: 12.6%/yr (about 13.5-14% with dividends), but a -60% worst drop (2008). That is roughly 2x an FD, not 3x.
- Monthly trend filter: 10.5%/yr with a -31% worst drop. It trades return for smaller crashes; it does not add return.
- Nothing tested comes close to 20%/year. Do not plan on it.
| Idea batch 1: 10 'forced trader' ideas (SIP, overnight, gap fade, after -2% day, VIX spike, last hour, first 30 min, pre-holiday, Fri-Mon, expiry day) | All 10 REJECT | Best was monthly-SIP timing (+0.48%/trade, 90 trades) but p=0.02 vs needed 0.005 and the random-entry check failed. Overnight drift is real before cost (+0.11%/night) but the 0.10% cost eats 88% of it. Daily data only 2018+ and 5-min only 2023+, so the tests are short |
| Theta Gainers intraday delta-neutral strangle on REAL option prices (73 traded days, Oct 2024 to Apr 2026) | A (as taught) REJECT, B (directional tweak) INCONCLUSIVE, C (hedged) REJECT | Gross edge about +Rs106/day, costs about Rs213/day. Net about -0.2% to -0.3% a month at assumed slippage, nowhere near the claimed 4% a month. As taught it is naked (worst day -Rs7,190 per lot, 6% of the quoted margin). Hedging caps the worst day but 4 extra orders a day cost more than they save. Only expiry day is consistently negative; other day-of-week cells are too small to trust |
| Batch 3: settlement mechanics (last-30-minute average on expiry day; 80 expiries) | T1 straddle REJECT, T2 protected REJECT, pin test: no real edge | The settlement price does behave like an average (spread ratio 0.68 vs 0.58 in theory), but option prices at 3:00 pm already reflect it (priced about 1.1x the model value). Selling the straddle: -Rs52 per trade after costs, +Rs32 before. Pin test passed its written rule only because the strike list is centred on the spot, so it proves nothing; it stays out of forward paper |
| Gold wheel on MCX Gold Mini options (feasibility only) | NOT TESTABLE | Upstox has no expired MCX option history (its docs say so; real calls returned nothing). Oldest option candle is 2026-09-28. Gold options are monthly only (about 12 cycles a year), and one Gold Mini lot is about Rs 14.6 lakh. Only forward paper recording is possible |
| Wheel strategy on NIFTY (index proxy: sell weekly puts, then calls after assignment; 81 weeks) | REJECT (closest miss) | Beat buy-and-hold by about Rs3,650 a week per lot (+6.6% vs -8.5% over the window) with a smaller worst drop, positive in both halves, but p=0.0116 vs the needed 0.00357. Most of the gain came from holding only about 60% of the index while it fell (+Rs12,200/wk in 48 down weeks, -Rs8,800/wk in 33 up weeks), and the benchmark started near an all-time high. Lost Rs150,692 in 4 weeks of March 2026. Not a single-stock wheel; 80 weeks cannot show crash risk |

## Selling note
A model-based 17-year stress (informational only) says the condor loses if real selling prices sit about 15% below flat-vol Black-Scholes, which is what the real data showed. Any positive result depends on assuming the textbook prices.

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


## Idea-factory loop (built 2026-10-18, paper only, NOT scheduled)
Folder: research/ideas/loop/ (README inside). Idea registry, tamper-evident trial ledger (the pass bar shrinks as total trials grow: 0.005 after batch 1, 0.0025 after a second batch of 10), a batch runner that refuses changed rules, a daily forward-paper job, promotion/retire rules (60 forward days, 20 trades, beats luck), and a weekly report.
Verified on synthetic data with a known edge (47 new tests, all pass). NOT yet run on the real NIFTY files or the live Upstox feed. Lot size and loss limit in the paper book are placeholders. Forward p<0.05 is not corrected across several forward ideas, so a promoted idea is still only a candidate for more paper time.
