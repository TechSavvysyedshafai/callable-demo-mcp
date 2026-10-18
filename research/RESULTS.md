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
## Planned (pre-registered 2026-10-18, quant analyst session; written BEFORE running)

### P1. Setup and data fetch
- Hypothesis: plumbing works (tests green, token valid, data downloads). No trading hypothesis; no trial consumed.
- Steps: run `research/scalp/tests/*.py`, `research/upstox/tests/test_upstox_parse.py`, `research/tests/*.py`; `research/upstox/check_setup.py`; `research/upstox/fetch_upstox.py`.
- Pass: tests exit 0; check_setup OK; files for 5-min index bars, India VIX, daily bars and expiry calendar are written under `research/data/`.
- Any failure is reported with its exact error text. Token is used only via environment variable; never printed.

**P1 result (2026-10-18):** all tests exit 0 (see report below); `check_setup.py` all 4 checks `[ OK ]` (107 expired NIFTY expiries, 2024-10-03 to 2026-10-13);
`fetch_upstox.py` wrote 55,438 five-minute bars (2023-10-19 to 2026-10-18, of which the dev file keeps 45,988 rows up to 2026-04-16 15:25), 743 VIX days, 1,981 daily bars (2018-10-22 to 2026-10-16; dev file 1,855 rows to 2026-04-16), 107 expiries. Source: Upstox v2 historical-candle + expired-instruments endpoints, downloaded 2026-10-18. No failures.
**Observation (not a failure):** `india_vix_day.csv` (to 2026-10-16) and `nifty_expiries.csv` (to 2026-10-13) are written UNSPLIT into `research/data/` and so extend past the 6-month holdout cut (2026-04-16). Index bars are split correctly. Recorded as a QA finding (P2).

### P2. Data-quality tool (`research/qa/data_quality.py`)
- Hypothesis: the downloaded data is clean enough to trust, or the defects are listed with counts. No trading hypothesis; no trial consumed.
- Checks (from `.claude/skills/market-data-engineering`): timezone naive/IST, session 09:15-15:25 bar starts, 75 bars per full day, short/gappy/missing days, weekends, duplicates, ordering, NaN, non-positive prices, high<low, open/close outside range, bar-return outliers > 5 sigma (each verified against the daily bar, never dropped), intraday-vs-daily agreement (tolerance fixed now: 0.10% on O/H/L/C), VIX sanity, expiry-calendar sanity, dev-window overlap.
- Pass: each check proven to fire on synthetic bad data AND stay silent on synthetic clean data (tests); real-data findings listed by category with counts; real defects fixed or documented, nothing deleted silently.
- Data window: dev files in `research/data/` only. Holdout file `~/.nifty_holdout` is never opened.

**P2 result (2026-10-18):** `research/qa/data_quality.py` + `research/qa/tests/test_data_quality.py` (passes; every check is proven to fire on injected bad data and to stay silent on clean data). Run on the dev files only. **Nothing was deleted or edited.** Findings by dataset and category:

| Dataset | Category | Count | Verdict |
|---|---|---|---|
| 5-min bars (45,988 rows, 617 days, 2023-10-19 to 2026-04-16) | NaN / duplicate timestamps / unsorted / price<=0 / high<low / open-close outside range | 0 each | clean |
| | days with exactly 75 bars | 607 of 617 | the other 10 are all explained below |
| | `short_day` (<75 bars) | 5 | REAL special sessions: Muhurat evening 2023-11-12, 2024-11-01 (12 bars each, 18:00-19:10), Muhurat 2025-10-21 (12 bars, 13:45-14:40), Saturday special sessions 2024-03-02 and 2024-05-18 (21 bars each) |
| | `long_day` (77 bars) | 5 | **DEFECT (documented):** 2025-04-25, 04-30, 05-08, 05-13, 05-21 each carry two phantom flat bars at 15:35 and 15:55 (open=high=low=close, volume 0). On all 5 days the 15:55 value equals the daily bar's close and differs from the 15:25 bar's close, so these are the official closing value appended as a fake bar, not trades |
| | `outside_session_hours` | 34 bars | 24 = the 2 evening Muhurat sessions; 10 = the phantom bars above |
| | `intraday_gap` / `missing_bars_in_gaps` | 12 gaps / 56 bars | all explained: 10 gaps (20 bars) around the phantom bars; 2 gaps (36 bars) = the lunch gap of the two Saturday special sessions. **No bars are missing inside any regular session** |
| | `late_first_bar` | 3 | the 3 Muhurat sessions |
| | `weekend_days` | 6 days (279 bars) | REAL trading days: Sat 2024-01-20, Sat 2024-03-02, Sat 2024-05-18, Sun 2023-11-12 (Muhurat), Sat 2025-02-01 and Sun 2026-02-01 (Budget days) |
| | `missing_day_vs_daily` / `day_not_in_daily_file` | 0 / 0 | every 5-min day has a daily bar and vice versa |
| | `vs_daily_open / high / low` (tol 0.10%) | 0 / 0 / 0 | agree |
| | `vs_daily_close` | 104 of 617 days | the last 5-min bar close is not the official close (median gap 0.04%, max 0.51% on 2024-06-04). Explanation (verified on the 5 phantom-bar days, assumed for the rest): daily close = the exchange's official closing value, which can differ from the last traded 5-minute bar. Matters for anything mixing 5-min closes with daily closes |
| | `outlier_5sigma` | 128 bars | KEPT. All 128 sit inside their daily bar's high/low and the day's high/low agree with the daily file (note: both come from the same vendor, so this shows consistency, not independent proof). 11 days hold 3+ outliers (28 on 2024-06-04 and 9 on 2024-06-05 = election-result volatility; 5 on Budget Sunday 2026-02-01). 11 outliers are followed by a >=80% reversal and all 11 are on those high-volatility days. No sign of isolated bad ticks |
| Daily bars (1,855 rows, 2018-10-22 to 2026-04-16) | integrity checks | 0 | clean |
| | `weekend_days` | 9 | real (Muhurat, Budget and special Saturdays) |
| | `calendar_gap_over_4d` | 1 | 2022-04-13 to 04-18 (Ambedkar Jayanti + Good Friday + weekend: real) |
| | `outlier_5sigma` | 9 | March 2020 COVID crash days: real |
| India VIX (743 rows, 2023-10-19 to 2026-10-16) | integrity, stale values, level range | 0 | clean (range plausible) |
| | dates vs NIFTY daily bars | 0 mismatches | consistent |
| | `outlier_5sigma` | 3 | 2024-06-05, 2024-08-05, 2025-04-07: real market events |
| | `weekend_days` | 6 | same special sessions as the bars |
| | **`beyond_dev_cutoff`** | **126 rows (2026-04-17 to 2026-10-16)** | **DEFECT (documented, not edited):** `fetch_upstox.py` saves VIX unsplit, so holdout-window values sit in the dev folder. No research script reads VIX past the 5-min dev cut-off, but the file is not clean |
| Expiry calendar (107 expiries, 2024-10-03 to 2026-10-13) | duplicates / unsorted / weekend / unparseable | 0 | clean |
| | `weekday_changes` | 13 | Thursday through 2025-08-28, **Tuesday from 2025-09-02** (rule change, matches the data; the exchange circular itself was not re-verified here). The other 12 are one-off holiday shifts to Wed/Mon (e.g. 2025-04-09, 2025-04-30, 2025-10-20, 2026-03-02, 2026-03-30, 2026-04-13) |
| | `gap_not_7_days` | 13 | the same 13 points |
| | `expiry_beyond_daily_data` / `beyond_dev_cutoff` | 26 / 26 | **documented:** 26 expiries (2026-04-21 to 2026-10-13) fall in the holdout window; the calendar file is unsplit. Cannot be checked against trading days |
| | lot size | not checkable | lot size is not in any file; stays an ASSUMPTION to verify against NSE circulars |

Implications (no frozen file edited): the backtest loaders group by calendar date, so the 5 special-session days (0.8% of days) and the 3 weekend days are treated as ordinary days. The engine's 15:00 no-entry / 15:15 flat times mean the evening Muhurat sessions cannot trade, but the Saturday sessions and Muhurat 2025-10-21 (13:45-14:40) can. The phantom 15:35/15:55 bars come after the 15:15 flatten time and cannot affect scalp exits. Whether to exclude these days is a decision for the owner; it was not changed here.

### P3. Sample of expired-option files + option-file QA
- Hypothesis: the saved option candles are complete enough to backtest on; where they are not, the gaps are counted. No trading hypothesis; no trial consumed.
- Data: `download_expired_options.py --underlying NIFTY --expiries 15 --strikes 5 --before 2026-04-16`, re-run until `0 failed`. **Deviation from the planner's literal command, on purpose:** without `--before` the script takes the 15 LATEST expiries (2026-07 to 2026-10), which all lie inside the 6-month holdout window (after 2026-04-16). Saving them in the dev folder would put holdout-period prices where research can read them. `--before` is a new additive option (default off) in the downloader; nothing else in the script changed. The 15 expiries used are the latest ones on or before the dev cut-off.
- Checks (added to `data_quality.py --options`): per-file integrity, candle coverage (bars present vs 75 per day with data), CE/PE strike symmetry, strike coverage vs where spot traded (share of 5-min bars whose ATM strike is outside the saved range), zero-volume share, volume spikes (>50x median), open-interest jumps (>5x median in one bar), rows after expiry.
- Pass: 0 failed downloads; every file passes the integrity checks; the gap / coverage numbers are reported whatever they are.

**P3 result (2026-10-18; downloaded 2026-10-18 from Upstox `/v2/expired-instruments/*`, 5-minute interval):**
Download: 15 expiries (2026-01-06 to 2026-04-13), ATM +/-5 strikes around the prior close, CE+PE = **330 files, 158,625 rows, 0 failed**; a second run saved 0 and failed 0 (resume works). Files are git-ignored under `research/data/expired_options/NIFTY/`.
Checks per category (option files):

| Category | Count | Meaning |
|---|---|---|
| NaN / duplicates / unsorted / price<=0 / high<low / open-close outside range / negative volume or OI / rows after expiry / bars outside 09:15-15:25 | 0 each | files are structurally clean |
| `candle_gap_within_day` | 1,050 bars | 99.34% of the expected 75 bars per day are present on days a file has data; the rest are minutes with no trade recorded |
| `trading_days_missing_in_file` | 3 of 2,132 file-days | a contract is missing a whole day only 0.14% of the time |
| `zero_volume_share` | 5,170 bars (3.3%) | price is carried forward with no trade. Concentrated far from expiry: 0.0-1.3% at 0-5 days left, 3.8% at 6, 8.6% at 7, 9.9% at 8-9 days |
| `zero_volume_near_atm` | 0 of 35,875 rows | no zero-volume bars within 100 points of spot, so the strikes a strategy would actually buy always had trades in that bar |
| `price_move_without_volume` | 0 | no inconsistent bars |
| `oi_zero` | 20 bars in 4 far-from-money put files | OI of 0 in a trading file: bad or empty OI snapshot (not used by any strategy) |
| `oi_big_drop` | 1 bar (2026-03-02_25300PE) | one unexplained >50% single-bar OI fall away from expiry day |
| **`spot_outside_saved_strikes`** | **1,734 of 5,175 tradeable 5-min bars = 33.5%** | **the ATM strike was NOT among the saved strikes** (see below) |

Strike coverage, in detail (tradeable day = the nearest expiry with >=1 day left): share of bars with no saved ATM strike, by days left to expiry: 1d 11%, 2d 16%, 3d 0%, 4d 25%, 5d 42%, 6d 37%, 7d 50%, 8d 99%. Cause (verified by arithmetic): the downloader centres the +/-5 strikes (250 points) on the close of the day BEFORE expiry, but a weekly NIFTY contract is traded for about 6 sessions, during which spot drifts away from that centre. Signals early in the week therefore have no contract to price. The predecessor's +/-12 download (600 points) should shrink this but their report still lists 114 unpriced signals; with +/-5 the 493 unpriced signals recorded above are consistent with this table. Skipped signals skew to large-move days, so a result computed only on priced signals is biased. **Impact: any option backtest on +/-5 files covers only about two thirds of the tradeable bars and is not a fair test of the signal.** The OI/volume checks found nothing that would invalidate the covered bars.
Note: `volume_spike` / `oi_jump` checks written first were dropped after calibration on real files: OI legitimately rises from ~1,000 to over 1,000,000 contracts as expiry approaches, and volume legitimately spikes 50x, so those thresholds flagged 84 and 193 of 330 files and meant nothing.

### P4. Adversarial review of the daily range-forecast PASS (pre-registered 2026-10-18 BEFORE any review number was computed)
- Claim under review (predecessor session; UNVERIFIED until reproduced below): `research/evaluate.py` on `nifty_day_dev.csv` -> 1,604 origins, candidate MAE 0.003960 vs best baseline ewma94 0.004214 (6.0% better), `ci_lower_gain` 9.4e-5, `n_trials` 1, verdict PASS.
- Target: log(high/low) of the NEXT day, forecast from days <= t. Candidate = fixed HAR blend 0.4*r[-1] + 0.3*mean(r[-5:]) + 0.3*mean(r[-22:]). No parameters were fitted. Data: dev daily file only (to 2026-04-16); holdout untouched. This review adds NO new strategy version, edits no frozen file, and does not call `log_trial` (the ledger is not touched).
- (a) Lookahead. Read `walk_forward` and `candidate.py`; plus two executable tests on the real data: (i) truncation: forecasts for every origin i < N-1 computed on rows[:N] must equal those from the full file, for N = 1,000 and 1,500; (ii) future-garbage: overwrite every row after N with random junk; the same forecasts must be unchanged. Any difference > 1e-12 = lookahead found.
- (b) Independent reproduction: a separate numpy script (`research/qa/repro_daily_mae.py`) that does not import the harness: own rolling windows, own MAE for candidate / random_walk / mean20 / ewma94, own moving-block bootstrap (block 5, 20,000 reps, alpha 0.05, own seed). Accept if MAEs match the harness within 1e-6 and the relative gain within 0.1 percentage point; the bootstrap bound is stochastic and is accepted within 20% of the harness value.
- (c) Placebo, two kinds, forecasts held fixed (candidate and the best baseline), only the realised targets are destroyed: (1) random permutation of the targets over the origins, 2,000 draws, seed 12345; (2) circular time-shift of the targets by every s in 30..N-30. Statistic: relative MAE gain of candidate over the best baseline. "Similar gain" (-> REJECT) = the observed gain is not above the 95th percentile of the placebo distribution (permutation p > 0.05) OR the placebo median gain is >= 50% of the observed gain. Rule applies to either placebo.
- (d) Stability: split the 1,604 origins into 3 consecutive chunks (`np.array_split`); report candidate and ewma94 MAE in each and each chunk's share of the total summed MAE gain. REJECT if one chunk holds more than 70% of the total gain.
- (e) Verdict: REJECT if (c) similar gain, or (d) one chunk > 70%, or (a) lookahead found. SURVIVES REVIEW if none of those AND (b) reproduces AND the candidate beats the best baseline in >= 2 of 3 chunks. Otherwise INCONCLUSIVE. Informational items that do NOT change the verdict: trial-count verification, special-session days in the target, pinball loss, results without the 2020 crash.

**P4 result (2026-10-18). Verdict: REJECT** (pre-registered trigger: one chunk holds more than 70% of the gain; it holds 96.1%).
Plain answer: the daily-lab "PASS" is real arithmetic but it is a crisis-period effect, not a lasting edge. Over the last ~2 years the candidate is slightly WORSE than the simple baseline. Do not use it to size or filter trades on the strength of this result.

| Check | Result |
|---|---|
| (b) Independent reproduction (numpy, no harness) | 1,604 origins; MAE candidate 0.003960198 / random_walk 0.004762486 / mean20 0.004294383 / ewma94 0.004214052; best baseline ewma94; gain 6.024%; bootstrap lower bound 9.35e-5. The harness gives the identical MAEs (differences ~1e-15), gain 6.024%, bound 9.41e-5. **Predecessor claim reproduced (6.0%, 9.4e-5).** |
| (a) Lookahead | None found. Code read: `walk_forward` gives the predictor `df.iloc[:i+1]` and scores bar i+1; `candidate.py` uses only that history. Executable tests (N=1000 and 1500; candidate and all 3 baselines): forecasts computed on truncated data and on data whose future was overwritten with random junk were identical to the full-data forecasts (max difference 0.0 in every case). |
| (c) Placebo, targets shuffled in time (2,000 draws) | candidate gain vs ewma94 **vanishes and reverses**: mean -6.27%, 95th percentile -5.02%, max -3.72% (observed +6.02%; permutation p = 0.0005). Circular time-shift (1,544 shifts): mean -6.27%, 95th pct -4.43%, p = 0.0006. Not "similar", so this trigger did not fire. (Why negative: the candidate reacts faster, so its forecasts are more spread out and are punished when they are not aligned with the real targets.) |
| (d) Three consecutive chunks (candidate MAE vs ewma94 MAE, relative gain, share of total gain) | **1** 2019-10-31 to 2021-12-22, n=535: 0.004950 vs 0.005682, +12.87%, **96.1%**. **2** 2021-12-23 to 2024-02-16, n=535: 0.003160 vs 0.003253, +2.85%, 12.2%. **3** 2024-02-19 to 2026-04-16, n=534: 0.003770 vs 0.003707, **-1.70%**, -8.3%. |
| Where the gain sits (informational) | by target year, share of total gain: 2019 5.5%, **2020 81.9%**, 2021 10.9%, 2022 5.8%, 2023 4.5%, 2024 -3.2%, 2025 -6.5%, 2026 1.2%. The four months 2020-03 to 2020-06 alone hold 67.5%. Without that window the gain is 2.38% (still above the 2% bar but no longer significant-looking; not tested, not pre-registered). |
| Other informational items | Pinball loss (quantile forecasts): candidate 0.001358 vs 0.001495 for each baseline (the three baselines share the same quantile rule, so this mostly reflects the candidate's own residual-quantile method). Dropping 13 flagged special/very-short-range days (24 origins; crude heuristic, may include genuinely quiet days): gain 6.13%, so special sessions do not drive it. Mean forecast level is the same for all (0.01147 vs 0.01146), so no level bias. |

Trials (unverified): `research/ledger.jsonl` is git-ignored and does not exist in this checkout, so `n_trials = 1` cannot be confirmed here. Git history shows exactly one version of `candidate.py` (commit 6eedfb6, never edited since) and the TimesFM candidate was only plumbing-tested, which is consistent with 1 but proves nothing about uncommitted local runs. The HAR weights 0.4/0.3/0.3 are fixed by hand, not fitted; whether they were chosen before looking at data is unknown.
Gate status: step 4 (adversarial review) = REJECT. The lab is NOT promoted. What would change the verdict: the same candidate beating ewma94 in the 2024-2026 chunk with a pre-registered window (needs new out-of-sample data, e.g. the holdout, which only the owner may open).
Files: `research/qa/repro_daily_mae.py`, `research/qa/review_daily_lab.py`, outputs `research/qa/daily_lab_review.json`.

### Predecessor claims NOT reproduced in this session (all UNVERIFIED here)
- Option-buying scalp on real candles at ATM +/-12 strikes (5,295 files): FAIL at slippage 0.10 / 0.20, 822 trades, net -Rs 73k / -Rs 85k, gross about -0.24 / -0.43 points per trade, 114 signals unpriced. Only 330 files at +/-5 (15 expiries, dev window) were downloaded here for QA; the strategy was not re-run. The +/-5 table above shows why a +/-5 run is biased; +/-12 narrows but does not remove that.
- Futures scalp FAIL (costs dominate): numbers in the first table of this file are the predecessor's, not re-run.
- Earlier option results (model-priced PASS, +/-5 real-candle FAIL) likewise: predecessor's numbers.
These were not re-run because the task scope here was setup, QA and the daily-lab review.

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
**Limited evidence:** about 26 years contain only a handful of large drawdowns (mainly 2008, then 2011 and the 2020 crash); every comparison below rests on a few episodes.

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
- B0's -59.9% drawdown matches the known Jan to Oct 2008 closing peak-to-trough, and its CAGR matches the raw price ratio (close 1,173 on 2000-10-31 to 24,197 on 2026-04-16, 25.5 years).

**Adversarial review** (skill `adversarial-review`, one line per item)
1. Lookahead: signals tested to be causal by truncation (identical when future bars are removed); +1/+5 day delay degrades gently; the leak test is caught. S2 uses the NEXT bar's date to know a month has ended (a calendar fact, not a price).
2. Leakage: only `nifty_day_long_dev.csv` is read; the holdout file is written outside the repo and never read. Dev ends 2026-04-16.
3. Trials: 3 strategies + B0, one run, no parameter was changed after seeing numbers (200-day, 10-month, 12% target and the cost grid were fixed first; commits 3390312 and the next one precede any run). No earlier sessions touched this data. Controls (shifts, leak, placebo) are checks, not strategies.
4. Controls: placebo above; no random-entry p-value is meaningful here (3 strategies, about 26 years).
5. Costs: the cost grid (0.10 / 0.25 / 0.50% per one-way trade) is an ASSUMPTION. It is deliberately harsh: a liquid index ETF or futures costs far less than 0.25% one way. At 0.10% S1 still gives up 2.5 pp, S2 1.8 pp, S3 4.0 pp, so the verdict does not hinge on costs, except S3 (turnover 17 full switches/yr) which is largely a cost story. Tax rates verified (above).
6. Fills: trades at the next open with no slippage beyond the assumed cost. NIFTY itself is not tradable; an index fund, ETF or futures would be used, adding tracking error not modelled.
7. Selection: nothing dropped; all years shown. S3's first year uses 59 bars of warm-up.
8. Regime and period: results flip between halves. In the first half (2000 to mid-2013) S1 and S2 are within 0.8 pp of B0 with half the drawdown (they pass the rule there). In the second half (2013 to 2026) S1 gives up 6.7 pp and S2 3.4 pp. The drawdown benefit rests on a few episodes: 2008 (B0 -51.8% in the year, S1 -22.0%, S2 -19.5%) and the 2020 crash (second-half drawdown B0 -38.5%, S2 -18.8%); in the calendar year 2020 S1 and S2 even beat B0 (+24.1% and +20.8% against +15.0%).
9. Arithmetic: independent loop agrees (above); known-answer tests by hand (15 tests).
10. Plausibility: Sharpe 0.2-0.4 and CAGR below the benchmark are what low-turnover trend filters usually deliver; nothing too good to be true.

**Verdicts**
- **S1 (200-day filter, checked daily): REJECT** as a replacement for buy-and-hold. It fails the pre-registered rule in the full sample (-3.8 pp) and in the second half (-6.7 pp), trades 7 times a year, and the bootstrap interval for the drawdown ratio (0.50 to 1.19) does not exclude "no better than B0".
- **S2 (10-month filter, checked monthly): INCONCLUSIVE** on risk reduction, but it does NOT meet the "useful" rule (full sample -2.1 pp against the allowed -1.5 pp; second half -3.4 pp). It halves the drawdown (ratio 0.52), trades about 2 times a year and keeps 10.5% a year, yet the bootstrap interval for the CAGR difference (-7.1 to +3.0 pp) and drawdown ratio (0.50 to 1.07) are wide. Deciding it would take more independent drawdown episodes than 26 years of NIFTY holds (other markets would be a new, separately pre-registered test).
- **S3 (volatility targeting): REJECT.** It is worse than B0 on return in every period (-6.8 pp full sample; bootstrap interval -10.7 to -3.0 pp excludes zero), does not shrink drawdowns more than the trend filters, and its daily re-sizing costs about 4 pp a year at 0.25%. (Not run, because it would be a new trial: a rebalance band to cut turnover.)

**Meets the pre-registered "useful" rule? No, none of S1, S2, S3.** Verdict: buy-and-hold index fund is the benchmark and nothing here beats it. The owner's 20% target is not reached by any of these rules or by the benchmark.
Next single step (owner's decision): keep buy-and-hold as the reference for any future idea; if drawdown comfort matters more than the last 2 to 3 pp of return, S2 is the only candidate worth a separately pre-registered test on other indices, and only with the owner's approval.

## 2026-10-18: "Intraday delta neutral" (Theta Gainers routine) on REAL NIFTY weekly options (branch claude/employee-deltaneutral)

### Planned (pre-registered 2026-10-18 BEFORE any strategy number was computed; not to be changed afterwards)
**Question.** A popular Indian YouTube teacher sells an intraday "delta neutral" option-selling routine. As taught (rules in `docs/strategies/reyaansh_delta_neutral_intraday.md`)
it is a NAKED short strangle with 25%-premium re-matching adjustments, a 30% stop at the straddle stage and a range exit; there is no hedge in the intraday version.
Does it, implemented mechanically exactly as documented, earn a positive, robust return after real costs and spreads on REAL NIFTY weekly option prices, and what are its worst days? Also test a hedged version.
**Mechanism.** The seller collects time decay (theta) and implied-volatility premium; the buyer on the other side pays for protection/lottery tickets. Adjusting keeps the book near delta-neutral but realises losses on the trending side.
**Trial cap = 3 variants, nothing else, no tuning.**
- A "as taught": rules 1-7 of the doc, naked strangle; on a confirmed breakout (two consecutive 15-minute closes beyond the same boundary) EXIT everything at the next 5-minute open.
- B "as taught + directional tweak": as A, but on a confirmed breakout buy back only the threatened leg and hold the other with a cost-to-cost stop (exit if its mark returns to the price at which it was sold); exit at 15:15 otherwise.
- C "hedged A": as A, plus at entry buy protective wings 200 points beyond each short strike (nearest 50 multiple); wings held to the exit and never adjusted. Adjustments move only the short legs; the maximum loss per day is therefore bounded (computed in the report).
**Universe.** NIFTY weekly options, DEV expiries only (dev cut-off 2026-04-16), every trading day from 2024-10-03 whose swing-range rule passes (doc interpretation). Expiry days included; results by days-to-expiry (0, 1, 2, 3-4, 5+). Quantity 1 lot (75).
**Costs.** `research/scalp/options/costs_opt.py OptionCostModel.side()` for EVERY order (adjustments add orders; counted), plus settlement STT for any leg still in the money at expiry (rule/rates to be verified on Upstox's brokerage page and cited with date; if not verifiable, say so). Slippage per fill swept Rs0.10 / 0.20 / 0.30 (assumed; no bid/ask in candles).
**Fills and marks.** Signals on 5-minute candle CLOSES; actions fill at the NEXT 5-minute candle OPEN (sold legs at open minus slippage, bought legs at open plus slippage). A missing needed candle means the action is skipped and counted (skipped entries, skipped adjustments reported).
**Delta.** Black-Scholes delta with each strike's own implied volatility inverted from its real candle price at the entry bar, rate 6.5%, time to expiry to 15:30 IST on expiry day. Only candles at or before the decision bar are used.
**Capital base (ASSUMPTION).** Rs1.2 lakh per lot for A and B (the teacher's quoted margin; real margin unverified). For C: max possible daily loss plus the same Rs1.2 lakh only if the hedged margin cannot be found; the choice is stated in the report. Return on capital per month and annualised, compared with the "4% a month" claim (UNVERIFIED claim from an interview title about his MONTHLY version).
**PASS RULE (fixed now).** A variant is "useful" only if at slippage Rs0.20: (a) mean daily net P&L per lot > 0 AND the 95% block-bootstrap CI of the mean (5-day blocks, 5,000 resamples) has lower bound > 0, AND (b) total net P&L >= 3 x the single worst day loss, AND (c) mean daily net P&L still > 0 at slippage Rs0.30, AND (d) the worst-day loss is smaller than 5% of the capital base. Otherwise: no demonstrated edge.
**Reported per variant and slippage.** Days traded and skipped, win rate, mean/median daily net, total net, worst day, max drawdown (Rs and % of capital base), longest losing streak, average adjustments per day, share of days ended by each exit reason (EOD, range exit, straddle stop, cost-to-cost stop), table by days-to-expiry. About 80 weeks cannot show crash-day risk.
**Data plan.** `fetch_upstox.py` (index bars, daily, VIX, expiry calendar), then `download_expired_options.py --underlying NIFTY --strikes 10 --before 2026-04-16` for all dev expiries since 2024-10-03, repeated until 0 failed, started only after 05:30 UTC (shared Upstox rate limit with another session). No result is reported from partial data.
**Ambiguities resolved in the code (fixed before running):** see the "Interpretations" list written with the Result entry; they are also stated in the module docstring of `research/deltaneutral/backtest.py`.

### Result (run 2026-10-18, one run, 3 variants x 3 slippages, no tuning; ledger `research/deltaneutral/ledger_deltaneutral.jsonl`; code `research/deltaneutral/`)
**Answer first: no.** Implemented mechanically as documented, the routine does NOT show a positive, robust return after real costs on real NIFTY weekly option candles. None of A, B, C meets the "useful" rule. At Rs0.20 slippage A averages -Rs107 a day, B -Rs57, C -Rs267 (per lot of 75), and every 95% interval includes zero, so the data cannot prove a loss either: they only show no demonstrated edge. The main reason is cost: A earns about +Rs106 a day before fees and pays about Rs213 a day in brokerage, STT and taxes (about 7.7 orders a day). The worst days are naked-strangle trend days: A -Rs7,190 on 2025-05-15 (range exit after two adjustments) and -Rs6,765 on 2024-11-28 (straddle stop), each about 6% of the Rs1.2 lakh base. About 80 weeks and 73 traded days cannot show crash-day risk; a gap day such as an election result would be far worse for the naked versions.

**Data (verified):** NIFTY 5-minute bars to 2026-04-16 (dev), 80 expiry calendars of real expired-option candles (3,355 files, ATM +/-10 strikes around the prior close; downloader pass 1 finished with 0 failed, 2026-10-18). The 2024-12-26 expiry has no files (the contract list gave none; 2 signal days lost). Window 2024-10-03 to 2026-04-16: 380 trading days, swing rule passes on 94 (of the 286 failures: 138 zone too narrow, 132 no swing on one side, 14 too wide, 2 no 09:40 bar).

**Capital bases (ASSUMPTION):** A and B Rs1,20,000 per lot (teacher's quoted margin; real margin unverified). C: Rs1,20,000 plus the widest possible intraday loss of the structure seen (widest single wing-to-short spread seen, 650 points after adjustments moved shorts toward the money; 2 spreads x 650 x 75 = Rs97,500) = Rs2,17,500, because the hedged margin could not be found. On a plain Rs1.2 lakh base C would read -0.58% a month at Rs0.20 (comparison only).
**Hedge bound for C (computed):** at entry the wings are 200 points out: held to expiry the loss is at most (200 - net credit) x 75 (about Rs10,000 before costs); intraday both spreads can carry value, so the bound is (400 - credit) x 75 (tested). Adjustments move the shorts toward the money and widen the spread to the old wings, up to 650 points in this sample, so "bounded" is true but the bound is far looser than 200 points. Realised worst C day: -Rs3,353 at Rs0.20.

**Main table (per lot of 75; Rs; slippage in premium rupees per fill):**
| Var | Slip | Days traded | Skipped (data) | Win % | Mean/day | Median | Total net | Worst day | Max DD (Rs / % base) | Losing streak | Adj/day | Orders/day | Mean 95% CI (5-day blocks) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.1 | 73 | 23 | 44 | -47 | -179 | -3,403 | -7,130 | -10,542 / -8.8% | 7 | 1.85 | 7.7 | -370 to 280 |
| A | 0.2 | 73 | 23 | 44 | -107 | -233 | -7,812 | -7,190 | -12,885 / -10.7% | 7 | 1.84 | 7.7 | -428 to 218 |
| A | 0.3 | 73 | 23 | 42 | -164 | -293 | -12,003 | -7,250 | -16,086 / -13.4% | 7 | 1.84 | 7.7 | -492 to 164 |
| B | 0.1 | 73 | 23 | 42 | 4 | -244 | 278 | -9,583 | -11,539 / -9.6% | 7 | 1.85 | 7.7 | -345 to 460 |
| B | 0.2 | 73 | 23 | 41 | -57 | -289 | -4,132 | -9,643 | -13,417 / -11.2% | 8 | 1.84 | 7.7 | -405 to 401 |
| B | 0.3 | 73 | 23 | 41 | -114 | -334 | -8,323 | -9,703 | -16,484 / -13.7% | 8 | 1.84 | 7.7 | -468 to 350 |
| C | 0.1 | 42 | 54 | 40 | -176 | -281 | -7,401 | -3,263 | -11,495 / -5.3% | 6 | 1.86 | 11.7 | -631 to 317 |
| C | 0.2 | 42 | 54 | 38 | -267 | -378 | -11,211 | -3,353 | -14,346 / -6.6% | 6 | 1.83 | 11.7 | -728 to 228 |
| C | 0.3 | 42 | 54 | 36 | -358 | -475 | -15,030 | -3,443 | -17,205 / -7.9% | 6 | 1.83 | 11.7 | -821 to 148 |

**Return on capital (not compounded; 4% a month is an UNVERIFIED claim from an interview title about the teacher's MONTHLY version, not tested here):**
| Var | Slip | Capital base (Rs) | Net / month on base | Worst / best month | Annualised (simple x12) | Total return over sample | Months |
|---|---|---|---|---|---|---|---|
| A | 0.1 | 120,000 | -0.15% | -5.8% / 4.7% | -1.8% | -2.8% | 19 |
| A | 0.2 | 120,000 | -0.34% | -5.9% / 4.7% | -4.1% | -6.5% | 19 |
| A | 0.3 | 120,000 | -0.53% | -6.1% / 4.6% | -6.3% | -10.0% | 19 |
| B | 0.1 | 120,000 | 0.01% | -6.3% / 4.9% | 0.1% | 0.2% | 19 |
| B | 0.2 | 120,000 | -0.18% | -6.3% / 4.8% | -2.2% | -3.4% | 19 |
| B | 0.3 | 120,000 | -0.37% | -6.4% / 4.7% | -4.4% | -6.9% | 19 |
| C | 0.1 | 217,500 | -0.21% | -2.1% / 1.9% | -2.6% | -3.4% | 16 |
| C | 0.2 | 217,500 | -0.32% | -2.2% / 1.7% | -3.9% | -5.2% | 16 |
| C | 0.3 | 217,500 | -0.43% | -2.3% / 1.5% | -5.2% | -6.9% | 16 |

**Exit reasons (share of traded days; B's range exit is a partial exit, so its day ends by EOD or cost-to-cost):**
| Var | Slip | eod | range_exit | straddle_stop | cost_to_cost | forced_close | Breakout days | Skipped adj. | Skipped exit candles | Forced-close days |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.1 | 25% | 63% | 12% | 0% | 0% | 46 | 0 | 0 | 0 |
| A | 0.2 | 25% | 63% | 12% | 0% | 0% | 46 | 0 | 0 | 0 |
| A | 0.3 | 23% | 63% | 14% | 0% | 0% | 46 | 0 | 0 | 0 |
| B | 0.1 | 44% | 0% | 12% | 44% | 0% | 46 | 0 | 0 | 0 |
| B | 0.2 | 44% | 0% | 12% | 44% | 0% | 46 | 0 | 0 | 0 |
| B | 0.3 | 42% | 0% | 14% | 44% | 0% | 46 | 0 | 0 | 0 |
| C | 0.1 | 31% | 52% | 17% | 0% | 0% | 22 | 0 | 0 | 0 |
| C | 0.2 | 31% | 52% | 17% | 0% | 0% | 22 | 0 | 0 | 0 |
| C | 0.3 | 29% | 52% | 19% | 0% | 0% | 22 | 0 | 0 | 0 |

**By days to expiry (calendar days to the expiry used), slippage 0.20:**
| Var | DTE | Days | Mean net | Total net | Win % | Worst |
|---|---|---|---|---|---|---|
| A | 0 | 24 | -313 | -7,503 | 42 | -7,190 |
| A | 1 | 15 | -304 | -4,565 | 40 | -3,093 |
| A | 2 | 12 | 336 | 4,034 | 50 | -2,773 |
| A | 3-4 | 10 | -136 | -1,355 | 60 | -3,535 |
| A | 5+ | 12 | 131 | 1,577 | 33 | -1,067 |
| B | 0 | 24 | -75 | -1,803 | 38 | -9,643 |
| B | 1 | 15 | -550 | -8,253 | 40 | -3,645 |
| B | 2 | 12 | 960 | 11,522 | 58 | -1,379 |
| B | 3-4 | 10 | -327 | -3,273 | 50 | -3,407 |
| B | 5+ | 12 | -194 | -2,325 | 25 | -2,035 |
| C | 0 | 22 | -347 | -7,638 | 32 | -3,353 |
| C | 1 | 10 | 90 | 903 | 50 | -829 |
| C | 2 | 5 | -314 | -1,570 | 40 | -1,432 |
| C | 3-4 | 3 | -640 | -1,919 | 67 | -3,001 |
| C | 5+ | 2 | -493 | -986 | 0 | -596 |
Cells hold 2 to 24 days; the only cell with a consistent sign across A and B is DTE 0 (expiry day), negative; do not read the rest.

**Skips and no-signal days (counts are identical across slippage):**
| Var | Slip | No swing range (rule failed) | Data skips (reason: days) |
|---|---|---|---|
| A | 0.1 | 284 {'no_swing_range': 284} | {'no_strike': 19, 'no_entry_bar': 2, 'no_option_files': 2} |
| A | 0.2 | 284 {'no_swing_range': 284} | {'no_strike': 19, 'no_entry_bar': 2, 'no_option_files': 2} |
| A | 0.3 | 284 {'no_swing_range': 284} | {'no_strike': 19, 'no_entry_bar': 2, 'no_option_files': 2} |
| B | 0.1 | 284 {'no_swing_range': 284} | {'no_strike': 19, 'no_entry_bar': 2, 'no_option_files': 2} |
| B | 0.2 | 284 {'no_swing_range': 284} | {'no_strike': 19, 'no_entry_bar': 2, 'no_option_files': 2} |
| B | 0.3 | 284 {'no_swing_range': 284} | {'no_strike': 19, 'no_entry_bar': 2, 'no_option_files': 2} |
| C | 0.1 | 284 {'no_swing_range': 284} | {'no_strike': 19, 'wing_unavailable': 31, 'no_entry_bar': 2, 'no_option_files': 2} |
| C | 0.2 | 284 {'no_swing_range': 284} | {'no_strike': 19, 'wing_unavailable': 31, 'no_entry_bar': 2, 'no_option_files': 2} |
| C | 0.3 | 284 {'no_swing_range': 284} | {'no_strike': 19, 'wing_unavailable': 31, 'no_entry_bar': 2, 'no_option_files': 2} |
Skipped entries are all "no strike with |delta| <= 0.25 inside the +/-10-strike file range" (19 days, every one 2 to 6 days to expiry) or a missing wing file (C, 31 days). Skipped adjustments: 0; skipped exit candles: 0; forced closes: 0 (liquid weekly strikes always had a candle). Because far-dated days are the ones skipped, the traded sample leans to 0 to 2 days to expiry (51 of 73 days).

**Pre-registered pass rule (slippage 0.20 for a, b, d; 0.30 for c):**
| Var | (a) mean>0 and CI low>0 @0.20 | (b) total>=3x worst day @0.20 | (c) mean>0 @0.30 | (d) worst day <5% of base @0.20 | USEFUL |
|---|---|---|---|---|---|
| A | False | False | False | False | **False** |
| B | False | False | False | False | **False** |
| C | False | False | False | True | **False** | 
 capital={'A': 120000.0, 'B': 120000.0, 'C': 217500.0} widest=650 C_on_margin_only={'0.1': -0.3854577691336713, '0.2': -0.5838933186577604, '0.3': -0.7827910801081506}

**Adversarial review** (skill `adversarial-review`; one line per item)
1. Lookahead: unit test scrambles every candle after 11:00 and shows all fills up to 11:00 unchanged; decisions use bars starting at or before the decision bar; swing zone uses only the 3 prior sessions. An extra-delay run was NOT done (it would be a new variant). 
2. Leakage: only `research/data/` dev files read; days after 2026-04-16 excluded; the 3 days after the last dev expiry (2026-04-13) were skipped, not priced from later files. Holdout untouched.
3. Trials: exactly 3 variants, one run each; the only change after first launch was a crash fix (KeyError when a strike's file does not exist; now counted as a missing candle; test added) made before any number was seen. 
4. Controls: no random-entry or placebo control (the trial cap forbids extra variants); with all intervals straddling zero none could rescue a pass. The statistic is days (73/73/42), not trades.
5. Costs: Rs20 per order (Basic plan; Plus is Rs30, which would be worse), STT 0.15% on sells (from 1 Apr 2026) applied to the whole window although the rate was 0.1% before then, so costs are overstated for 2024-25 days (this flatters the strategy's *gross* conclusion not at all: even before fees A earns only about +Rs106 a day, against a Rs7,000 worst day). Exercise STT: 0.15% of intrinsic value (Upstox explainer read 2026-10-18; the charges page itself was not read); irrelevant because nothing is held to expiry.
6. Fills: next-bar open plus an assumed slippage; real spreads on expiry-day wings and far strikes may be wider than Rs0.30. The cost-to-cost stop compares the mark with the slippage-adjusted sale price, so a flat market already triggers it (B ends 44% of days that way).
7. Selection: skipped days listed above; far-dated days are over-skipped; C trades only 42 days, a different and shorter sample than A/B.
8. Regime: A and B are -Rs42/-Rs171 and +Rs111/-Rs219 per day in the first and second half of the sample; C -Rs573 in the second half. The 5 worst days make up about 40% of A's total loss days; one NIFTY expiry-day trend (DTE 0: A -Rs7,503 total, 24 days) carries a large share.
9. Arithmetic: `crosscheck.py` re-prices every fill from the raw CSVs with hand-written fee arithmetic: all 73/73/42 days agree with the harness to Rs0.000000.
10. Plausibility: gross about +Rs100 a day on a Rs1.2 lakh margin is what a modest premium-selling edge looks like; nothing too good.
Lot size: 75 units used for the whole window as instructed; real NIFTY lot sizes changed over 2024-26 (an Upstox article read 2026-10-18 says 65 currently), so rupee figures are for 75 units, not exact lots.

**Verdicts:** **A: REJECT** (fails all four pass tests; costs are twice the gross edge even at Rs0.10 and the worst day is 6.0% of the base). **B: INCONCLUSIVE** (about zero at Rs0.10, negative at 0.20 and 0.30, interval -405 to +401; separating a real small edge from zero would need several hundred more signal days). **C: REJECT** (loses at every slippage, costs Rs303 a day against Rs36 gross because it pays 4 extra orders; it does cap the worst day at -Rs3,353 but the base is Rs2.2 lakh). **"Useful" rule met by none.**
**Next single step (owner):** stop here on this routine; if option selling is of interest, record live bid/ask for several weeks before any further test, because cost, not direction, decided this result.
