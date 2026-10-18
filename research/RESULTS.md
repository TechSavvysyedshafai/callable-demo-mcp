# Results log (honest record; newest last)

Numbers from the Upstox-token session (2026-10-18/19). The planning session has no network access to Upstox, so it
could not independently reproduce these runs. Data: NIFTY 5-minute bars, dev set only (hidden 6-month holdout never read).

| Test | Data | Result | Verdict |
|---|---|---|---|
| Futures scalp, momentum signal | real index bars, ~500 sessions, costs at 1 Apr 2026 rates | 1,466 trades, 36% wins, gross ~ -Rs 38k, costs Rs 15.9 lakh, net -Rs 16.3 lakh, break-even 15.3 pts/trade, p vs random 0.25 | FAIL |
| Options scalp, MODEL prices (Black-Scholes), Tuesday-expiry assumption | index bars + India VIX | net +Rs 34k, p 0.025 | PASS (artefact) |
| Options scalp, MODEL prices, real expiry calendar | 300 sessions from Oct 2024 | net +Rs 18k, Sharpe 0.38, p 0.0498 | marginal PASS (model prices) |
| Options scalp, REAL expired-option candles (ATM +/-5 strikes, 2,332 files, 107 expiries) | slippage 0.10 / 0.20 / 0.30 Rs per fill | net -Rs 52k / -62k / -76k, ~687 trades, gross -0.09 pts/trade at 0.10, p vs random 0.09 / 0.075 / 0.12 | **FAIL at every slippage** |

Conclusions
- The model-based option "pass" did not survive real option prices. Modelled premiums flattered the strategy.
- No demonstrated edge in this momentum signal for NIFTY futures or ATM option buying. Do not paper trade or trade it.
- Known gap: 493 signals could not be priced (no saved strike near the money, because only ATM +/-5 strikes around the PRIOR close
  were downloaded). These skew to large-move days. A wider strike download would close this; it is unlikely, but not proven,
  to change the verdict. Candles carry no bid/ask, so slippage is assumed (a limitation that can only matter if an edge existed).
- Trial count so far for this signal: 2. Every new strategy idea tried on this data raises the bar for the next.

---

## 2026-10-18: Low-turnover daily NIFTY strategies (branch claude/employee-lowturnover)

### Planned (pre-registered BEFORE any strategy number was computed; not to be changed afterwards)

**Question.** Owner wants about 20%/yr, steady. Scalping failed on real data. Can a slow, low-turnover rule on daily NIFTY 50
match buy-and-hold with much smaller drawdowns (or beat it)? The honest benchmark is buy-and-hold (an index fund).
**Mechanism.** Equity drawdowns cluster in high-volatility, below-trend regimes; stepping aside in those regimes may cut drawdowns.
The counter-party who loses is whoever buys into falling trends; we do not assume this works, our prior is "no edge beyond the benchmark".
**Data.** Upstox daily NIFTY 50 bars, 2000-01-03 to today, split with `kite_data.write_split(holdout_months=6)`. DEV data only; the newest 6 months go to the
hidden holdout, which is not read. Bias to state: NIFTY 50 is a PRICE index, it excludes dividends (about 1.2-1.5%/yr), so every
CAGR here (benchmark and strategies, while invested) is understated by roughly that amount; cash leg is assumed 6.5%/yr.
**Trials.** Max 3 strategies + 1 benchmark, no tuning, parameters fixed now.
- B0: buy and hold NIFTY.
- S1: at each close, if close > 200-day simple moving average, hold NIFTY from the NEXT open, else cash at 6.5%/yr. Checked daily.
- S2: at the last trading day of each month, hold NIFTY for the next month if close > 10-month average of month-end closes, else cash at 6.5%/yr.
- S3: exposure = min(1, 12% / forecast annualised vol). Forecast = existing `research/candidate.py` HAR-style forecast of log(high/low), converted to annualised
  volatility; information up to the close, trade the NEXT open; cash earns 6.5%; no leverage.
**Costs (assumptions, not verified facts).** All-in cost per switch (round trip, in % of traded value): 0.10%, 0.25%, 0.50%. Headline = 0.25%.
**Tax.** Verify current Indian equity capital-gains rates from an official source and cite the date; after-tax variant for S1 and S2 (short vs long term).
**Metrics.** CAGR, annualised vol, max drawdown, Sharpe, Calmar (CAGR/maxDD), % time invested, switches per year, worst calendar year. Full dev sample,
first half, second half (by date), and each calendar year. Block-bootstrap 90% CI for (strategy minus benchmark) CAGR and for the max-drawdown ratio.
About 26 years is limited evidence (a handful of independent bull/bear cycles).
**PASS ("useful") at 0.25% cost, in the full sample AND BOTH halves:** (CAGR within 1.5 pp of B0 AND max drawdown at least 30% smaller than B0) OR
(CAGR at least 1 pp above B0 with max drawdown not worse). If none qualifies: verdict is "buy-and-hold index fund is the benchmark and nothing here beats it".
**Controls / stop rule.** Stop at the first of: trial cap reached, criteria met, criteria clearly failed. Any change after seeing numbers is a new trial and will be logged as such.

**Pre-run implementation details, fixed before any strategy number was computed** (these fill gaps in the plan above; they are not tuning):
- Timing: a decision at day t's close trades at day t+1's open. Day t+1 return = w(t-1) x overnight gap + w(t) x (open-to-close) + (1-w(t)) x cash daily rate (6.5%/252-day compounding).
- Cost: each one-way trade of size |change in exposure| pays the all-in cost c on the traded value (c = 0.10 / 0.25 / 0.50%). This is conservative (c is charged on every buy and every sell, so a full in-and-out costs 2c).
- All strategies and B0 are scored over the SAME window, starting when every signal is defined (about late 2000), and B0 pays the entry cost too. "Halves" = the evaluated dates cut at the midpoint.
- S3 conversion: sigma_ann = 252^0.5 x predict()["mean"] / (2 x (2/pi)^0.5) (Parkinson: E[ln(H/L)] = 1.596 x daily sigma). `predict` is called with the last 60 bars (it only reads the last 60), so it is the unmodified `candidate.py`. The daily range excludes the overnight gap, so it understates true volatility; no adjustment is made.
- "Switches per year" = sum of |change in exposure| per year (one full in or out = 1). For S3 this is turnover in full-position units.
- Bootstrap: circular moving-block bootstrap on paired daily returns (strategy, B0), block 63 trading days, 2,000 resamples, seed 0, 90% interval (5th-95th percentile); block 21 shown as sensitivity. Max-drawdown ratio = strategy maxDD / B0 maxDD (below 1 = smaller drawdown).
- After-tax: current rates only (20% short-term under 12 months; 12.5% long-term above Rs 1.25 lakh per year), applied to the whole history as a counterfactual; losses carried forward; Rs 1.25 lakh exemption ignored in the headline (conservative, owner capital unknown); interest on cash leg untaxed (favours the strategies); B0 taxed once as if sold at the end.
- Controls (not extra strategies, not trials): +1 day signal shift, a deliberately leaky signal, and a random on/off placebo matched on % time invested and switch count.
- Trials ledger for this work: `research/lowturn/ledger_lowturn.jsonl` (separate from `research/ledger.jsonl`, so the daily-lab trial count is not disturbed).

### Result (run 2026-10-18, one run, 3 strategies + 1 benchmark, no tuning; trial ledger `research/lowturn/ledger_lowturn.jsonl`)

**Answer first.** None of the three rules is "useful" under the rule we fixed in advance. Buy-and-hold NIFTY (the index fund) is the benchmark and nothing here beats it.
The two trend filters (S1, S2) roughly halve the worst drawdown (about -30% against -60%) but give up 2 to 4 percentage points of return per year. The volatility-targeting rule (S3) is worse on return and trades far too often.
Nothing here gets near 20% a year: buy-and-hold made 12.6% a year (price index only, before dividends), the cash alternative is assumed at 6.5%.

Data: Upstox daily NIFTY 50, 6,662 bars 2000-01-03 to 2026-10-16 downloaded; the newest 126 bars (6 months) went to the hidden holdout (never read). Dev = 6,536 bars to 2026-04-16.
Scored from 2000-10-31 (first day all signals exist). Data checks: no duplicates, no NaN, no OHLC violations, no gaps over 6 days; the largest moves are real events (May 2004, 2008, May 2009, 2020).
**Bias:** NIFTY 50 is the price index; it omits dividends (about 1.2-1.5%/yr). That understates B0 by more than the strategies (B0 is always invested).
**Limited evidence:** about 26 years contain only about three large drawdowns (2001, 2008, 2020) plus 2011 and 2022; every comparison below rests on a handful of episodes.

**Full dev sample, cost 0.25% per one-way trade** (2000-10-31 to 2026-04-16):

| | CAGR | Vol | Max DD | Sharpe | Calmar | % invested | Switches/yr | Worst yr |
|---|---|---|---|---|---|---|---|---|
| B0 | 12.6% | 21.2% | -59.9% | 0.38 | 0.21 | 100.0% | 0.04 | -51.8% (2008) |
| S1 | 8.9% | 15.1% | -29.6% | 0.23 | 0.30 | 71.5% | 7.39 | -22.0% (2008) |
| S2 | 10.5% | 16.2% | -31.2% | 0.32 | 0.34 | 71.6% | 1.89 | -19.5% (2008) |
| S3 | 5.9% | 13.5% | -32.0% | 0.03 | 0.18 | 81.8% | 17.14 | -26.5% (2008) |

**First half** (2000-11-01 to 2013-07-01), 0.25%:

| | CAGR | Vol | Max DD | Sharpe | Calmar | % invested | Switches/yr |
|---|---|---|---|---|---|---|---|
| B0 | 13.6% | 25.1% | -59.9% | 0.39 | 0.23 | 100.0% | 0.08 |
| S1 | 12.9% | 18.1% | -27.8% | 0.42 | 0.46 | 65.5% | 5.45 |
| S2 | 12.8% | 19.8% | -31.2% | 0.39 | 0.41 | 67.4% | 1.50 |
| S3 | 5.9% | 13.8% | -32.0% | 0.03 | 0.18 | 69.9% | 22.50 |

**Second half** (2013-07-02 to 2026-04-16), 0.25%:

| | CAGR | Vol | Max DD | Sharpe | Calmar | % invested | Switches/yr |
|---|---|---|---|---|---|---|---|
| B0 | 11.7% | 16.3% | -38.5% | 0.39 | 0.30 | 100.0% | 0.00 |
| S1 | 5.0% | 11.4% | -29.6% | -0.06 | 0.17 | 77.6% | 9.31 |
| S2 | 8.3% | 11.7% | -18.8% | 0.22 | 0.44 | 75.9% | 2.27 |
| S3 | 5.9% | 13.2% | -26.9% | 0.03 | 0.22 | 93.7% | 11.84 |

**Cost sweep (CAGR / max drawdown, full sample):**

| Cost per one-way trade | B0 | S1 | S2 | S3 |
|---|---|---|---|---|
| 0.10% | 12.6% / -59.9% | 10.1% / -27.3% | 10.8% / -30.4% | 8.6% / -29.8% |
| 0.25% | 12.6% / -59.9% | 8.9% / -29.6% | 10.5% / -31.2% | 5.9% / -32.0% |
| 0.50% | 12.6% / -59.9% | 6.9% / -36.2% | 10.0% / -32.6% | 1.4% / -46.1% |

**Pre-registered rule at 0.25%** (CAGR difference vs B0 in pp; drawdown as a share of B0's drawdown; clause A = within 1.5 pp and drawdown <= 70% of B0's; clause B = >= +1 pp and drawdown not worse):

| | Full sample | First half | Second half | Useful? |
|---|---|---|---|---|
| S1 | -3.8 pp, DD 0.49x, fail | -0.7 pp, DD 0.46x, ok | -6.7 pp, DD 0.77x, fail | **NO** |
| S2 | -2.1 pp, DD 0.52x, fail | -0.8 pp, DD 0.52x, ok | -3.4 pp, DD 0.49x, fail | **NO** |
| S3 | -6.8 pp, DD 0.53x, fail | -7.7 pp, DD 0.53x, fail | -5.9 pp, DD 0.70x, fail | **NO** |

**Block-bootstrap 90% intervals at 0.25% (strategy minus B0; 63-day blocks, 2,000 resamples; 21-day blocks in brackets):**

| | CAGR difference | Max-drawdown ratio (strategy / B0) |
|---|---|---|
| S1 | -9.4 to +1.8 pp [-9.5 to +2.1] | 0.50 to 1.19 [0.50 to 1.14] |
| S2 | -7.1 to +3.0 pp [-7.6 to +3.4] | 0.50 to 1.07 [0.51 to 1.09] |
| S3 | -10.7 to -3.0 pp [-10.9 to -3.0] | 0.58 to 1.08 [0.61 to 1.07] |

**After-tax (current Indian rates applied to the whole history; Rs 10 lakh start; no exemption / with Rs 1.25 lakh per year exemption):**

| Cost | | Pre-tax CAGR | After-tax CAGR | Tax drag (pp/yr) | Episodes | Avg hold (days) | Gain taxed as short-term |
|---|---|---|---|---|---|---|---|
| 0.10% | B0 | 12.6% | 12.1% / 12.1% | 0.56 / 0.56 | 1 (sold at end) | n/a | n/a |
| 0.10% | S1 | 10.1% | 9.0% / 9.1% | 1.10 / 1.00 | 94 | 70 | 14.7% |
| 0.10% | S2 | 10.8% | 9.9% / 10.0% | 0.96 / 0.88 | 24 | 276 | 3.9% |
| 0.25% | B0 | 12.6% | 12.1% / 12.1% | 0.56 / 0.56 | 1 (sold at end) | n/a | n/a |
| 0.25% | S1 | 8.9% | 7.9% / 8.0% | 0.96 / 0.86 | 94 | 70 | 14.0% |
| 0.25% | S2 | 10.5% | 9.6% / 9.7% | 0.93 / 0.85 | 24 | 276 | 3.3% |
| 0.50% | B0 | 12.6% | 12.1% / 12.1% | 0.56 / 0.56 | 1 (sold at end) | n/a | n/a |
| 0.50% | S1 | 6.9% | 6.1% / 6.2% | 0.73 / 0.61 | 94 | 70 | 13.4% |
| 0.50% | S2 | 10.0% | 9.1% / 9.2% | 0.88 / 0.79 | 24 | 276 | 2.6% |

Full tables (all three costs, both halves, every calendar year) are in `research/lowturn/results/lowturn_results.md` and `.json`.

**Tax (verified 2026-10-18 on the official Income Tax Department pages incometaxindia.gov.in/w/tax-on-short-term-capital-gains and /tax-on-long-term-capital-gains):**
listed equity held under 12 months: short-term gain taxed at 20% (it was 15% before 23-07-2024); held over 12 months: long-term gain taxed at 12.5% on the part above Rs 1.25 lakh per financial year. Surcharge and 4% cess are NOT included (they would raise every tax figure slightly). Budget changes after the pages' text were not separately checked.
Frequent switching adds tax drag, but less than one might fear, because most S1 and S2 trades are over 12 months or have small gains: at 0.25% cost, B0 loses 0.56 pp/yr to tax (all deferred to the end), S1 loses 0.96 pp (+0.4 pp more than B0) and S2 0.93 pp (+0.4 pp more). S1's average holding is 70 days, 14% of its gains are taxed as short-term; S2's average is 276 days, 3%.
After tax: B0 12.1%, S1 7.9%, S2 9.6%. Assumptions that favour the strategies: interest on the cash leg is untaxed (FD interest is taxed at slab rates). Assumptions that favour B0: its tax is deferred to the end, and current rates are applied to all years (before April 2018 long-term equity gains were untaxed).

**Controls and checks**
- Extra signal delay (cost 0.25%): S1 CAGR 8.9% -> 8.2% (1 day) -> 8.2% (5 days); S2 10.5% -> 10.0% -> 10.0%; S3 5.9% -> 6.8% (1 day). Gradual or flat, no collapse and no flip: no sign of lookahead. A deliberately leaky signal (peeks at the next day's move) shows 137% a year with Sharpe 6.2 and is obviously caught.
- Random on/off placebo (1,000 draws, same average time-in and time-out lengths as S1 and S2): median max drawdown about -53%, 5th percentile -63%. S1 (-29.6%) and S2 (-31.2%) are far better than random timing, so the drawdown reduction is a property of trend following, not of simply being out of the market part of the time. But placebo CAGR (8.9% S1-matched, 10.5% S2-matched) equals the strategies' own CAGR: the rules do not add return, they only shift when the risk is taken.
- Independent re-computation (`lowturn/crosscheck.py`, plain loops, no shared code): B0 12.60% / -59.86% and S1 8.82% / -29.84% against 12.64% / -59.90% and 8.86% / -29.61% in the main engine. Agreement within 0.04 pp CAGR and 0.25 pp drawdown (the engine adds the overnight and intraday legs within a day; the check compounds them).
- B0's -59.9% drawdown matches the known Jan to Oct 2008 closing peak-to-trough, and its CAGR matches the raw price ratio (1,283 to 24,197 over 25.5 years).

**Adversarial review** (skill `adversarial-review`, one line per item)
1. Lookahead: signals tested to be causal by truncation (identical when future bars are removed); +1/+5 day delay degrades gently; the leak test is caught. S2 uses the NEXT bar's date to know a month has ended (a calendar fact, not a price).
2. Leakage: only `nifty_day_long_dev.csv` is read; the holdout file is written outside the repo and never read. Dev ends 2026-04-16.
3. Trials: 3 strategies + B0, one run, no parameter was changed after seeing numbers (200-day, 10-month, 12% target and the cost grid were fixed first; commits 3390312 and the next one precede any run). No earlier sessions touched this data. Controls (shifts, leak, placebo) are checks, not strategies.
4. Controls: placebo above; no random-entry p-value is meaningful here (3 strategies, about 26 years).
5. Costs: the cost grid (0.10 / 0.25 / 0.50% per one-way trade) is an ASSUMPTION. It is deliberately harsh: a liquid index ETF or futures costs far less than 0.25% one way. At 0.10% S1 still gives up 2.5 pp, S2 1.8 pp, S3 4.0 pp, so the verdict does not hinge on costs, except S3 (turnover 17 full switches/yr) which is largely a cost story. Tax rates verified (above).
6. Fills: trades at the next open with no slippage beyond the assumed cost. NIFTY itself is not tradable; an index fund, ETF or futures would be used, adding tracking error not modelled.
7. Selection: nothing dropped; all years shown. S3's first year uses 59 bars of warm-up.
8. Regime and period: results flip between halves. In the first half (2000 to mid-2013) S1 and S2 are within 0.8 pp of B0 with half the drawdown (they pass the rule there). In the second half (2013 to 2026) S1 gives up 6.7 pp and S2 3.4 pp. The drawdown benefit rests mainly on 2008; 2020 is a V-shape the filters mostly caught late.
9. Arithmetic: independent loop agrees (above); known-answer tests by hand (15 tests).
10. Plausibility: Sharpe 0.2-0.4 and CAGR below the benchmark are what low-turnover trend filters usually deliver; nothing too good to be true.

**Verdicts**
- **S1 (200-day filter, checked daily): REJECT** as a replacement for buy-and-hold. It fails the pre-registered rule in the full sample (-3.8 pp) and in the second half (-6.7 pp), trades 7 times a year, and the bootstrap interval for the drawdown ratio (0.50 to 1.19) does not exclude "no better than B0".
- **S2 (10-month filter, checked monthly): INCONCLUSIVE** on risk reduction, but it does NOT meet the "useful" rule (full sample -2.1 pp against the allowed -1.5 pp; second half -3.4 pp). It halves the drawdown (ratio 0.52), trades about 2 times a year and keeps 10.5% a year, yet the bootstrap interval for the CAGR difference (-7.1 to +3.0 pp) and drawdown ratio (0.50 to 1.07) are wide. Deciding it would take more independent drawdown episodes than 26 years of NIFTY holds (other markets would be a new, separately pre-registered test).
- **S3 (volatility targeting): REJECT.** It is worse than B0 on return in every period (-6.8 pp full sample; bootstrap interval -10.7 to -3.0 pp excludes zero), does not shrink drawdowns more than the trend filters, and its daily re-sizing costs about 4 pp a year at 0.25%. (Not run, because it would be a new trial: a rebalance band to cut turnover.)

**Meets the pre-registered "useful" rule? No, none of S1, S2, S3.** Verdict: buy-and-hold index fund is the benchmark and nothing here beats it. The owner's 20% target is not reached by any of these rules or by the benchmark.
Next single step (owner's decision): keep buy-and-hold as the reference for any future idea; if drawdown comfort matters more than the last 2 to 3 pp of return, S2 is the only candidate worth a separately pre-registered test on other indices, and only with the owner's approval.
