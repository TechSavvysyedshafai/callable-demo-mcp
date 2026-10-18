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

---
## Planned (pre-registered 2026-10-18, branch claude/employee-selling; written BEFORE any data was downloaded or any backtest run)

### SELL1. Weekly NIFTY iron condor (SELLING defined-risk premium), REAL expired-option prices
- **Question:** option buyers lose on average because implied volatility (India VIX mean about 14%) exceeds realised (NIFTY about 10%). Does SELLING that premium with defined risk earn a positive, robust return after real costs and spreads? Purpose: measure income AND tail risk honestly, not to promote selling. Paper research only; no leverage beyond the structure.
- **Mechanism / who is on the other side:** buyers of short-dated options pay an implied-volatility premium over what is later realised (volatility risk premium). The seller is paid for bearing rare large moves.
- **Trials:** cap = 2 variants (V1, V2) of ONE structure; all parameters fixed now, no tuning.
- **Data:** NIFTY weekly expiries, DEV only. Expired-option 5-minute candles from `research/upstox/download_expired_options.py --underlying NIFTY --strikes 10 --before 2026-04-16` (repeated until 0 failed). Index 5-minute bars and daily closes from `research/data/` (`fetch_upstox.py`). Expiry calendar `research/data/nifty_expiries.csv`; expiries from 2024-10-03 and never after 2026-04-16.
- **Structure (1 lot = 75 units; points and rupees per lot):** at entry SELL the call at the short strike nearest to spot x 1.012 (rounded UP to a multiple of 50) and SELL the put nearest spot x 0.988 (rounded DOWN to a multiple of 50); BUY a long call at short call + 150 and a long put at short put - 150. Spot = close of the NIFTY 5-minute bar at the entry bar.
- **Entry:** first 5-minute bar at or after 09:30 IST on the trading day nearest on-or-before (expiry date - 7 calendar days). Sell legs fill at the option candle OPEN minus slippage; buy legs at OPEN plus slippage. If ANY of the four legs has no candle at the entry bar, SKIP the week and count it.
- **V1:** hold to expiry; settle each leg at intrinsic value of the official NIFTY close (daily bar) on expiry day.
- **V2:** V1 plus a stop. At every 5-minute bar close from the entry bar on, mark each leg at its last known candle close; if total mark-to-market loss >= 2 x net credit received, exit all four legs at the NEXT bar's open (shorts bought back at open + slippage, longs sold at open - slippage); if no later bar exists, use the last known close with slippage.
- **Costs:** `research/scalp/options/costs_opt.py` `OptionCostModel.side()` for every order (Rs20 brokerage per order, STT 0.15% of sell premium, exchange, SEBI, stamp, GST). For legs that expire in the money add settlement STT 0.15% x intrinsic x quantity per ITM leg. No brokerage on legs that expire worthless or are cash-settled. Slippage per fill swept at Rs0.10 / 0.20 / 0.30 (an assumption: candles carry no bid/ask).
- **Capital base (ASSUMPTION, real broker margin not available to me):** return on capital = P&L / (2 x maximum structure loss per lot); maximum structure loss is bounded by width x 75 = 150 x 75 = Rs11,250, so the base used is a fixed Rs22,500 per lot.
- **PASS RULE (fixed now).** A variant is "useful" only if at slippage Rs0.20: (a) mean weekly net P&L > 0 AND the block-bootstrap 90% confidence interval of the mean has lower bound > 0 (blocks of 4 consecutive weeks, 5,000 resamples), AND (b) total net P&L over the sample >= 2 x the single worst week loss, AND (c) mean weekly net P&L is still > 0 at slippage Rs0.30. Otherwise: **no demonstrated edge from selling.**
- **Report per variant and slippage:** weeks traded, weeks skipped, win rate, mean/median weekly net, total net, worst week, max drawdown (Rs), longest losing streak, % of weeks the short strike was breached, comparison with doing nothing. About 80 weeks is about 1.5 years and contains no crash comparable to 2008 or 2020, so it cannot reveal tail risk.
- **TAIL STRESS (secondary, MODEL-BASED, informational; cannot change the PASS RULE):** long daily NIFTY (2000 to dev cut-off) and India VIX history (dev only), a weekly condor every historical week with the same percentage rule, credit from Black-Scholes at week-start VIX CALIBRATED to the real-price sample (ratio and spread reported). Distribution of weekly P&L, worst 10 weeks, maximum drawdown, number of weeks losing the full structure width.

**Interpretations fixed now (before data), where the brief was open:**
1. "Net credit" for the V2 stop = sum of sell fills minus sum of buy fills per unit at entry (after slippage). Stop fires when (current mark cost to close the four legs - net credit) >= 2 x net credit, evaluated per unit.
2. "Next bar" = the next 5-minute timestamp. Each leg exits at its own candle OPEN at that timestamp; if that leg has no candle then, its last known close is used with slippage.
3. Block bootstrap = overlapping moving blocks of 4 consecutive traded weeks, 5,000 resamples, fixed seed; the 90% interval is the 5th to 95th percentile of the resampled means.
4. Settlement STT is charged on EVERY ITM leg (long and short), which is conservative (Indian STT on exercise is levied on the option buyer); the rule is verified against Upstox's charges page before any P&L is computed (result recorded below).
5. Breach = the expiry-day NIFTY close is beyond the short call strike (above) or short put strike (below).
6. Max drawdown = largest peak-to-trough fall of cumulative weekly net P&L, starting equity 0.
7. Tail-stress wing = 150 / median real-sample entry spot, as a percentage of spot, strikes not rounded to 50; entry is the close of the trading day nearest on-or-before each week's Thursday, expiry the next such day; T = 7/365, r = 6.5%, sigma = India VIX close / 100.
8. The lot size is held at 75 for every week as the brief states. The exchange changed NIFTY's lot size over this window (my recollection: 25, 75, 65; NOT verified); points are unaffected, rupees scale linearly.
9. Weeks the data cannot price because strikes were not downloaded (ATM is set from the previous close before expiry, +/-10 strikes) are skipped and counted; I will report coverage by checking only the skipped count (no P&L) before deciding whether any extra download is needed, and say so.

---
## 2026-10-18: SELL1 results. Weekly NIFTY iron condor, SELLING premium, real expired-option prices (branch claude/employee-selling)

**Answer first.** No. On 80 real weeks (Oct 2024 to Apr 2026, dev data only) selling this weekly condor LOST money after costs in both versions, so the pre-registered "useful" rule fails (all three parts) and the verdict is **no demonstrated edge from selling**. Per lot (75 units) at the middle spread assumption (Rs0.20 per fill): V1 (hold to expiry) averaged **-Rs642 a week**, **-Rs51,359 in total**; V2 (with a stop) averaged **-Rs464 a week**, **-Rs37,138 in total**. Even with perfect fills and no fees the structure averaged -Rs437 (V1) and -Rs260 (V2) a week: it collected about 54.5 points of premium a week and paid out about 60.4 (V1). The loss is not a cost story. The 90% interval for the mean (-Rs1,469 to +Rs460 for V1) still includes zero, so 80 weeks cannot prove the true average is negative; they give no support to it being positive. What it means for money: on the assumed Rs22,500 per lot of capital, V1 would have lost 228% of that capital in 80 weeks (the assumption would not have survived), so this is not an income strategy as specified. Trials used: 2 of 2.

**Deviations from the brief (all decided before looking at any P&L; none changes a parameter):**
1. The `download_expired_options.py --strikes 10` download (3,355 files, "0 failed") covered only ATM +/-10 strikes around the close BEFORE expiry, but the condor is built from the spot 7 days earlier. Result: 76 of 81 weeks lacked at least one leg file (found from skip counts only; no P&L had been printed). I added `research/selling/download_needed.py`, which downloads exactly the four contracts each week needs (strikes from the entry-bar close, same file names, resumable, dev only); 129 files saved. Total 3,484 files. Sample = 81 dev expiries (2024-10-03 to 2026-04-13); the 2026-04-21 expiry lies after the 2026-04-16 cut-off and was not used.
2. One expiry (2024-12-26) returns EMPTY candle lists for every contract from Upstox (also in the original download, which silently ignores empty results, so it still said "0 failed"). That week is skipped and counted: **1 skipped, 80 traded**.
3. Entry on 2025-10-21 (expiry 2025-10-28) is the Diwali Muhurat session (the data has 12 bars, 13:45 to 14:40), so the rule "first bar at or after 09:30 on the nearest trading day" entered at 13:45. Kept as the rule says; one week.
4. India VIX history from Upstox starts 2009-03-02, so the tail stress cannot include 2008.
5. Costs: the pre-registered 0.15% STT is used for every week. The statutory rates before 1 Apr 2026 were lower (premium 0.10%, exercise 0.125%). Verified on 2026-10-18 from secondary sources only (HDFC Securities' Budget 2026 note and INDmoney, both saying STT on options premium rose from 0.10% to 0.15% and on exercised options from 0.125% to 0.15% from 1 Apr 2026); Upstox's own brokerage page could not be opened from this environment and the official Finance Act text was not read. Using the lower rates changes V1's mean from -Rs642 to -Rs632. STT on exercise is in law paid by the option buyer; charging it on every ITM leg (as pre-registered) is conservative. Exchange charges on cash settlement are not added (assumption, not verified; small).
6. The lot size is held at 75 as the brief says; the exchange changed it over this window (not verified), points are unaffected.

**Results (per lot of 75 units, rupees, after fees and slippage; sample 2024-10-03 to 2026-04-13):**

| Variant | Slip (Rs/fill) | Traded | Skipped | Win rate | Mean/wk | Median/wk | Total | Worst week | Max drawdown | Longest losing streak | Short strike breached | Stopped | 90% CI of the mean (4-week blocks, 5,000 resamples) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | 0.10 | 80 | 1 | 56% | -612 | +2,146 | -48,961 | -9,155 | -51,728 | 4 | 48% | 0% | -1,439 to +490 |
| V1 | 0.20 | 80 | 1 | 56% | -642 | +2,116 | -51,359 | -9,185 | -53,436 | 4 | 48% | 0% | -1,469 to +460 |
| V1 | 0.30 | 80 | 1 | 56% | -672 | +2,086 | -53,757 | -9,215 | -55,145 | 4 | 48% | 0% | -1,499 to +430 |
| V2 | 0.10 | 80 | 1 | 55% | -441 | +2,146 | -35,283 | -7,695 | -42,053 | 4 | 48% | 19% | -1,212 to +588 |
| V2 | 0.20 | 80 | 1 | 55% | -464 | +2,116 | -37,138 | -7,755 | -43,426 | 4 | 48% | 19% | -1,230 to +566 |
| V2 | 0.30 | 80 | 1 | 54% | -550 | +1,959 | -44,011 | -7,815 | -49,577 | 4 | 48% | 20% | -1,312 to +482 |

Reading it: in a bit over half the weeks the condor earned a few thousand rupees (median +Rs2,100), but in the 25 weeks (V1) the index closed beyond a long strike each cost about Rs4,700 to Rs9,200, and 48% of weeks breached a short strike (the short strikes sit only about 0.6 to 0.85 of a typical weekly standard deviation away, taking VIX 14% or realised 10%). Mean fees were Rs145 a week (V1) and Rs161 (V2). V2's stop fired in 15 of 80 weeks; in those weeks V1 would have lost an average of Rs7,170 and the stopped trade lost Rs6,222, and only 1 of the 15 would have finished profitable, so the stop helped modestly by cutting the worst weeks but did not turn the mean positive.

**Pre-registered rule (slippage Rs0.20 and 0.30):** V1: (a) mean > 0 and CI lower bound > 0: NO; (b) total >= 2 x worst week: NO (total is negative); (c) mean > 0 at Rs0.30: NO. V2: NO, NO, NO. **Neither variant is "useful".**

**Doing nothing:** earns Rs0 (or about Rs2,250 over the 80 weeks if the assumed Rs22,500 per lot sat in cash at 6.5%). Both variants are far below that. Return on capital (assumed base Rs22,500 = 2 x Rs11,250 width bound; real broker margin was not available to me): V1 -228% over 80 weeks, V2 -165%.

**Controls and checks (diagnostics only; not trials; `research/selling/diagnostics.py`, `crosscheck.py`):**
- Independent recomputation (`crosscheck.py`, csv module and plain loops, costs re-derived by hand): same 80 weeks, total net -Rs51,359.16 (V1) and -Rs37,137.54 (V2), maximum weekly difference Rs0.00.
- Lookahead: the brief takes spot from the entry bar's CLOSE but fills at its OPEN (a five-minute peek). Delaying entry by one and two bars, and taking the strike spot from the previous bar's close, only works on weeks whose strikes do not change (other strike files were not downloaded), so I compared each shifted run with the base on the SAME weeks: V1 mean -Rs192 (+1 bar) vs base -Rs200 on those 60 weeks; +2 bars (55 weeks) shifted -Rs113 vs base +Rs23; previous-bar strikes -Rs159 vs base -Rs216 (52 weeks). Gradual change, no collapse and no flip: no sign of a leak. Weeks whose strikes moved when entry moved by 5 minutes (about 20 of 81) averaged about -Rs1,970 for V1, so volatile opens matter.
- Halves: V1 first 40 weeks -Rs223 a week, last 40 weeks -Rs1,061 a week (the last 40 weeks start about July 2025). V2: -Rs78 and -Rs851.
- Skipped week: 1 (the empty-data expiry); traded vs skipped comparison therefore has no power.

**TAIL STRESS (MODEL-BASED, informational, does not enter the pass rule; `research/selling/stress.py`):** 893 historical weeks, 2009-03-05 to 2026-04-16 (India VIX starts 2009-03-02, so 2008 is NOT covered; the 2020 crash is). Every week uses the same percentage rule (short +/-1.2%, wings 0.607% of spot = 150 points at the median real spot of 24,724, strikes not rounded), credit = Black-Scholes at the prior-day VIX close x a calibration ratio, rescaled to a constant notional (spot 24,724) so years are comparable, costs as above.
- Calibration ratio (real fill credit at Rs0.20 / flat-vol Black-Scholes credit at the prior-day VIX, 80 real weeks): median **0.849**, mean 0.881, standard deviation 0.160, quartiles 0.768 to 0.947, range 0.614 to 1.350, correlation with VIX 0.48 (the ratio is not constant; flat-vol Black-Scholes over-prices these strikes by about 15%, probably skew and VIX being a 30-day measure).
- With the median ratio: mean -Rs710 a week, total -Rs634,397, win rate 49%, standard deviation Rs5,238, 5th to 95th percentile -Rs7,433 to +Rs6,035, maximum drawdown **-Rs647,157**, **365 of 893 weeks (41%) ended beyond a long strike (full structure width lost)**. The worst 10 weeks are all within Rs8,200 to Rs8,600: with a defined-risk condor the maximum loss is capped near width x 75 less credit, so the worst weeks are 10 of about 370 near-cap weeks and carry little extra information (dates in `results/stress_results.json`). The COVID window 2020-02-15 to 2020-04-30 (11 weeks, largest weekly move -17.7%): total -Rs39,885, worst week -Rs7,293, 10 of 11 weeks at full width. The defined risk did what it should: no week lost more than about Rs8,600 per lot.
- Sensitivity to the ratio: ratio 0.768 (25th percentile): total -Rs1,064,732; ratio 0.947 (75th): -Rs123,881; ratio 1.0 (uncalibrated Black-Scholes at VIX): **+Rs157,207**, max drawdown -Rs135,546. So whether selling this structure earns anything in the model depends entirely on assuming it can be sold at the full Black-Scholes price; at the prices actually seen it does not.
- Limits: flat-vol Black-Scholes, one ratio for all eras, fills at the open, no bid-ask widening in crashes, no margin or circuit-limit effects, no gap through the wings, costs at today's rates. Only about 1.5 years of real prices stand behind the calibration.

**Not verified / assumed:** the Rs0.10 to 0.30 slippage per fill (candles have no bid/ask; wings 150 points out may trade wider); broker margin and capital; exchange charges on cash settlement; the lot size history; quality of Upstox candles for illiquid far-OTM strikes (a wing with no print at the entry bar would have been skipped, and none were).

**Adversarial review** (skill `adversarial-review`):
1. Lookahead: entry uses only candles at or before the entry bar, except that the pre-registered strike spot is the entry bar's close (5-minute peek); shifts of one and two bars and previous-bar strikes change results gradually (above). The stop reads closes only and exits at the NEXT bar's open (tested). Expiry settlement uses the official daily close of the expiry day, which is the settlement the contract uses.
2. Leakage: expiries 2024-10-03 to 2026-04-13 only; dev cut-off 2026-04-16; the holdout was never read. The VIX history request ends at the cut-off.
3. Trials: 2 (ledger `research/selling/ledger_selling.jsonl`), no parameter changed after seeing numbers. The data-coverage fix was decided from skip counts. The diagnostics (shifts, STT sensitivity) are controls, not strategies.
4. Controls: no random-entry null was built; with a negative mean, 80 weeks and one structure, it could only confirm the result. Same-week entry-shift controls above.
5. Costs: brokerage Rs20 per order (8 orders when stopped, 4 otherwise), STT on sells and ITM settlement, slippage sweep; survives nothing because it loses before costs. Cheaper statutory STT does not change the sign.
6. Fills: fills at the candle OPEN plus/minus slippage assume a market order fills near the open; real far-OTM wings may be wider, and stop exits after a fast move would likely be worse (a gap through the stop is only partly captured because exit is at the next bar's open).
7. Selection: 1 of 81 weeks skipped (empty vendor data), after fixing the coverage problem. A first version of the data (strikes 10) would have skipped 76 of 81 weeks and, because skips favour weeks where the market stayed close to its start, would have been biased.
8. Regime: losses cluster in Oct 2024 to Apr 2025 and Sep 2025 to Apr 2026; the second half is much worse than the first; one volatility regime, no 2008-type event.
9. Arithmetic: reproduced independently (above) and by hand on week 2024-10-03 (spot 26,032.7, short put 25,700, long put 25,550, credit 45.35, index closed 25,250 below the long put, loss 150 - 45.35 = 104.65 points = Rs7,849 before fees; the model gives gross -104.65).
10. Plausibility: a 48% short-strike breach rate with strikes 1.2% away and a positive median but negative mean is what a thin-margin short-volatility structure looks like; nothing too good to be true.

**Verdicts.** **V1: REJECT** as an income strategy (fails every part of the pre-registered rule, the mean is negative before costs, and no flaw found in the data or code would reverse that; the 90% interval is wide enough that I cannot say the true mean is negative). **V2: REJECT** (same rule failures; the stop reduces the worst week from -Rs9,185 to -Rs7,755 and the average loss by about Rs180 a week, but not enough). Neither is "useful"; the question "does selling premium with defined risk beat doing nothing" is answered NO for this parameterisation, and INCONCLUSIVE for selling in general (other strikes, widths or regimes were not tested and may not be, given the trial cap). Gate step reached: none (fails gate step 3, real prices).
**Next single step (owner's decision):** stop here on weekly NIFTY condor selling; do not paper trade it. If the owner wants the volatility-premium idea tested further, it needs a new, separately pre-registered question (for example record live bid/ask for several weeks first).

---
## Planned (pre-registered 2026-10-18, branch claude/employee-ideas; written BEFORE any backtest of Task 5 was run)
**Task 5: test the 10 forced-trader ideas in `docs/ideas/IDEAS_BATCH1_2026-10-18.md`, exactly as written.** Hypotheses, rules, cost, pass rule, trial count (exactly 10) and Bonferroni alpha (0.05 / 10 = 0.005) are those in that file; nothing below changes them. Where the file is ambiguous I chose the most literal reading and write it down here. Code, data checks and tests were prepared before any trade return was computed; only data coverage and calendar checks (no returns) were looked at.

**Data actually available (regenerated today with `research/upstox/fetch_upstox.py`, dev files only; the holdout went to `~/.nifty_holdout` via the existing script and was NOT opened):**
- NIFTY daily: 1,855 rows, 2018-10-22 to 2026-04-16 (the file says "2000.." but the repo's fetch script only pulls the last ~8 years; I did NOT go further back, because a longer window would be a different test).
- NIFTY 5-minute: 2023-10-19 to 2026-04-16 (the script pulls 3 years; Upstox minute data starts Jan 2022 but was not used).
- India VIX daily: 617 rows, 2023-10-19 to 2026-04-16. So idea 5 only has about 2.5 years.
- Real NIFTY weekly-expiry list (`nifty_expiries.csv`, 2024-10-03 to 2026-04-21) is used only to CHECK my expiry-day rule for idea 10.
- Daily file contains 9 weekend special sessions (Muhurat / budget Saturdays) and a few weekday Muhurat sessions. They are rows like any other (not removed); this is a stated assumption.

**Literal readings (all fixed now):**
1. *Trade return* = direction x (exit / entry - 1) - 0.001 (0.10% of notional per round trip, same for long and short). Zero-cost version drops the 0.001. Index levels stand in for futures (no basis, no roll, fills at the stated bar open/close print; assumption).
2. *Idea 1.* "Month" = calendar month. Trading days = rows of the daily file. Enter at close of the 2nd-last row of month M, exit at close of the 3rd row of month M+1. Last (partial) month in the file is skipped.
3. *Idea 2.* Every consecutive pair of rows: long at close(t), exit at open(next row). Trial = this overnight leg. The intraday leg (open to close, long) is reported as information only, not a trial.
4. *Idea 3.* gap = open(t) / close(previous row) - 1. Trade only if |gap| > 0.007 (strict). Gap up: short; gap down: long; open(t) to close(t).
5. *Idea 4.* "Down 2% or more" = close(t)/close(previous row) - 1 <= -0.02. Long at next row's open, exit at that row's close.
6. *Idea 5.* VIX rise = vix_close(t) / vix_close(previous VIX row) - 1 >= 0.15. Long NIFTY at the same date's close, exit at the close of the 3rd NIFTY row after. Every signal is a separate trade even if they overlap (nothing in the rule says skip); signals whose exit is past the data end are dropped.
7. *Time labels (ideas 6, 7).* A 5-minute bar labelled T opens at T. "Price at T" = open of bar T. Idea 6: r = open(15:15) / open(14:15) - 1; r > 0 long, r < 0 short, r = 0 no trade; enter at open of bar 15:15, exit at CLOSE of bar 15:25 (= 15:30). Idea 7: first 30-minute return = close(bar 09:40) / open(bar 09:15) - 1 (known at 09:45); sign up = long, down = short, zero = no trade; enter open(bar 09:45), exit open(bar 15:15). A day missing any needed bar is skipped and counted.
8. *Idea 8.* Holiday = at least one Monday-to-Friday date strictly between two consecutive rows that is not a row (so a normal Friday-to-Monday is not a holiday; Thursday-to-Monday with Friday closed is). Long at close of the earlier row, exit at open of the later row. The holiday calendar comes from the data itself (the published calendar is known in advance, so it is knowable at time t).
9. *Idea 9.* Every Friday row whose date + 3 days is also a row (Monday): long at Friday close, exit Monday close. Friday or Monday closed: no trade, counted as skipped.
10. *Idea 10.* Expiry day = Thursday for dates up to 2025-08-28, Tuesday from 2025-09-02. If that weekday is not a trading row (holiday) the expiry is the PREVIOUS trading row (the exchange rule). I apply this to the whole file (the Thursday rule also covers Oct 2018 to early 2019, before weekly NIFTY options existed; I did not verify the launch date, a small known flaw, about 20 Thursdays of about 380). I will check the rule against the real list for 2024-10 to 2026-04 BEFORE looking at returns. Direction = sign of close(t-1)/close(t-2) - 1 (zero: no trade); open(t) to close(t).
11. *Bootstrap p (all ideas).* Moving-block bootstrap of the chronological per-trade net returns, block = 5 trades, 10,000 resamples, seed 20261018, resampled means centred on the sample mean (null: true mean 0); one-sided p = (1 + count of resampled means >= observed mean) / 10,001. The pre-registration gave no block length; 5 is my fixed choice.
12. *Random-entry null (all ideas).* Candidate trades = every possible start of the SAME template (same entry/exit bars, same holding length in rows) in the same data. Draw the same number of trades at random without replacement (matching each real trade's holding length), give them the real trades' directions in random order (so the long/short mix and market drift are the same), subtract the same cost. 10,000 draws, p = (1 + draws with mean >= observed mean) / 10,001. If a rule trades EVERY candidate (idea 2) the null is the rule itself and p = 1 by construction.
13. *Halves.* The calendar midpoint of the data window used by that idea (daily 2018-10-22..2026-04-16; 5-minute and VIX 2023-10-19..2026-04-16). A half with no trades counts as "not positive".
14. *Verdict.* SURVIVES = all of (a) net mean > 0, (b) bootstrap p < 0.005, (c) null p < 0.005, (d) positive net mean in both halves, (e) >= 60 trades. INCONCLUSIVE = (a) and (b) pass but one of (c), (d), (e) fails. REJECT = otherwise.
15. *Controls that are not trials:* zero-cost mean (and its bootstrap / null p, for information), and for ideas that decide and fill at the same price (3, 5, 6, 7) a one-step-later-entry check (lookahead diagnostic). They do not change any verdict.
**Max trials: 10. Stop rule: report all 10 whatever the outcome; no reruns after seeing numbers.**

**Addendum before the run (still no trade returns computed):** my first expiry rule for idea 10 missed one real expiry (the list says 2025-10-20) because Tue 2025-10-21 is a Diwali Muhurat evening session, a row in the data but not a regular day. Fix, decided from the calendar alone: for the expiry rule only, weekend rows and Muhurat days (2018-11-07, 2021-11-04, 2022-10-24, 2024-11-01, 2025-10-21) are not regular days, so an expiry falling on one moves to the previous regular day. Check: all real expiries in the file to 2026-04-16 are matched and none invented. Muhurat dates: 2021-11-04 confirmed by NSE holiday lists, 2024 and 2025 by 12-bar sessions in the data, 2018 and 2022 from memory (they are not on expiry weekdays). Other ideas keep Muhurat/weekend rows as ordinary rows, as pre-registered.

---
## 2026-10-18: Task 5 results. Idea batch 1, ten "who is forced to trade?" rules (branch claude/employee-ideas)

**Answer first.** None of the 10 ideas survives. All 10 are **REJECT**. Nothing reached even INCONCLUSIVE, which needs a positive net mean and a bootstrap p below 0.005. Six ideas (1, 2, 3, 4, 5, 8) have a positive mean after the harsh 0.10% cost but none is statistically separable from luck at alpha 0.005. For your money: do not trade any of these, and none goes to the paper-signal recorder. Trials used: 10 of 10 (`research/ideas/ledger_ideas.jsonl`).

| # | Idea | Trades | Mean net per trade | Mean at zero cost | Bootstrap p | Random-entry p | First half (n, mean) | Second half (n, mean) | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | SIP / salary inflows | 90 | +0.477% | +0.577% | 0.0228 | 0.0460 | 45, +0.604% | 45, +0.350% | REJECT |
| 2 | Overnight (close to next open) | 1,854 | +0.013% | +0.113% | 0.2299 | 1.0000* | 929, +0.045% | 925, -0.021% | REJECT |
| 3 | Fade the gap (>0.7%) | 299 | +0.011% | +0.111% | 0.4268 | 0.0241 | 205, +0.045% | 94, -0.065% | REJECT |
| 4 | After a -2% close, long | 50 | +0.233% | +0.333% | 0.1208 | 0.0024 | 40, +0.294% | 10, -0.013% | REJECT |
| 5 | After VIX +15%, long 3 days | 9 | +0.472% | +0.572% | 0.0422 | 0.2356 | 3, +2.000% | 6, -0.292% | REJECT |
| 6 | Last-hour return, trade 15:15-15:30 | 612 | -0.116% | -0.016% | 1.0000 | 1.0000 | 306, -0.118% | 306, -0.114% | REJECT |
| 7 | First 30 min sign, trade 09:45-15:15 | 612 | -0.095% | +0.005% | 0.9999 | 0.4231 | 306, -0.114% | 306, -0.076% | REJECT |
| 8 | Pre-holiday close to open | 107 | +0.054% | +0.154% | 0.1650 | 0.2595 | 50, +0.030% | 57, +0.076% | REJECT |
| 9 | Friday close to Monday close | 343 | -0.166% | -0.066% | 0.9505 | 0.9847 | 170, -0.273% | 173, -0.062% | REJECT |
| 10 | Expiry day, follow prior day | 390 | -0.101% | -0.001% | 0.9905 | 0.4591 | 195, -0.142% | 195, -0.060% | REJECT |

* Idea 2 trades every night, so the random-entry null is the rule itself and p = 1 by construction. Idea 5 has only 9 trades and idea 4 only 50 (the minimum is 60). Windows: daily ideas 2018-10-22 to 2026-04-16 (halves split at 2022-07-19); ideas 5, 6, 7 on 2023-10-19 to 2026-04-16 (midpoint 2025-01-16).

**Reading it in plain words.**
- Before costs there is something in two places. Idea 2: NIFTY rose +0.113% a night on average while the open-to-close leg lost 0.06% a day (intraday leg: information only, 1,855 days). The zero-cost bootstrap p for overnight is 0.0001. The 0.10% round-trip cost eats 88% of it, leaving +0.013% with p 0.23, and the second half is negative. Idea 1 (a 5-day hold around the month turn, +0.58% before cost per trade, +0.48% after) is the nearest miss: bootstrap p 0.023 and random-entry p 0.046, both above the corrected 0.005, from only 90 trades over 7.5 years. Out of 10 ideas, a p of 0.02 to 0.05 is what luck alone produces. I cannot call it an edge and cannot rule it out; the pre-registered rule says REJECT.
- Ideas 6, 7, 9 and 10 make nothing or less even at zero cost (-0.016%, +0.005%, -0.066%, -0.001% per trade): no edge before costs. Ideas 3 (gap fade) and 4 (after a big drop) have a small positive average, but idea 3 is negative in the second half and idea 4 has only 10 trades there.
- Idea 4 beats random entries (p 0.0024) but its bootstrap p is 0.12 and it has 50 trades, so it fails.

**Deviations and literal readings (all pre-registered before the run; see "Planned" above and its addendum):**
1. Data are shorter than the idea file says: daily 2018-10-22 to 2026-04-16 (not 2000); 5-minute and VIX only 2023-10-19 onward. This is what `fetch_upstox.py` gives; I did not pull longer history because that would be a different test. Idea 5 therefore has 9 signals and can never reach 60 trades.
2. The bootstrap block length (5 trades) and the random-entry null design were not specified; both are fixed in "Planned".
3. The idea 10 expiry rule was corrected before any return was computed (Muhurat day, addendum). After the fix it reproduces every real expiry in `nifty_expiries.csv` up to 2026-04-16 and invents none (unit test). The Thursday rule is also applied before weekly NIFTY options existed (Oct 2018 to early 2019, about 20 of 390 trades): launch date not verified, small effect.
4. Skipped signals: idea 6: 1 day, idea 7: 2 days (missing bars or special sessions), idea 9: 23 Fridays (Friday or Monday closed), others 0.

**Verified / assumed / unknown.**
- Verified: arithmetic reproduced by an independent plain-Python script for ideas 1, 2, 3, 4, 6, 7, 8, 9 (max difference 4e-19; `research/ideas/crosscheck_ideas.py`; ideas 5 and 10 are covered by unit tests only); 31 unit tests with hand-computed answers pass; the 12 other repo test files still pass; the expiry rule matches the real expiry list; the holdout directory was never opened (the existing fetch script wrote it); 2021-11-04 as a Muhurat/holiday day was checked against NSE holiday lists.
- Assumed: index levels stand in for futures (no basis, roll, margin or lot size); fills exactly at the bar open or close print with only the flat 0.10% cost. The idea file says about 15 points measured (about 0.06%), so 0.10% is generous; at 0.06% only idea 2 would clear the 0.005 bootstrap threshold, and it would still fail the random-entry test by construction and the second half. Muhurat and weekend sessions stay as ordinary rows in the daily file (except for the expiry rule); Muhurat dates 2018-11-07 and 2022-10-24 are from memory.
- Unknown: whether anyone can capture the overnight drift after realistic costs (not testable under the no-variants rule); anything before 2018 or on other indices; whether the vendor's daily "open" equals the exchange's official open.

**Adversarial review (skill `adversarial-review`).**
1. Lookahead: signals use only data known at decision time (unit tests: signals of ideas 3, 6, 7, 10 do not change when later prices change). Weak spot: rules that decide and fill at the same print. Controls only (not trials): entering one step later changes the gross mean as follows. Idea 3 on the 5-minute window (62 trades): +0.0003% to -0.150%, so the fade needs the very first print and a real order would not get it. Idea 5 (9 trades): +0.572% to +0.012%. Idea 6: -0.016% to -0.010%. Idea 7: +0.005% to +0.007%. These show the gap-fade and VIX results are fragile; no verdict changes, all are REJECT either way.
2. Leakage: only the dev files; last bar and last VIX row 2026-04-16; the real-expiry list was used only to check the calendar.
3. Trials: exactly 10, in `ledger_ideas.jsonl`; no rerun after seeing numbers (the one rule fix came before any return was computed). Bonferroni 0.005 applied. At an uncorrected 0.05 only idea 1 passes both tests, which is why the correction matters.
4. Controls: random-entry null (same count and holding, same long/short mix, same cost), halves, zero-cost version. No sign-flip placebo: it would only restate the zero-cost column.
5. Costs: flat 0.10% per round trip on every trade, long and short. Overnight holds carry margin interest that is not included.
6. Fills: at open/close prints (see item 1).
7. Selection: skip counts above; short or special sessions are skipped for ideas 6 and 7.
8. Regime and period: 7.5 years (2.5 for five-minute and VIX data), including the 2020 crash; not checked how much of idea 4's gain is 2020. Expiry weekday, STT and lot-size changes inside the window are not priced separately (flat cost).
9. Arithmetic: reproduced independently (above).
10. Plausibility: overnight +0.113% a night against -0.06% intraday is large but a known pattern for indices whose open reflects a pre-open auction; nothing else looks too good.

**Verdicts:** all ten **REJECT** (idea 1 is the nearest miss at p 0.023 / 0.046). Gate step reached: none (all fail gate step 2). **Next single step (owner's decision):** close batch 1. Following idea 1 or 2 further would need a new, separately pre-registered question, counted as new trials, and a longer history.

---
## Task 6 (2026-10-18): idea-factory loop built (`research/ideas/loop/`). No idea was tested; trial count stays at 10.

What was built, as specified in `docs/ideas/LOOP_SPEC.md`: a registry (the 10 Batch 1 ideas, all `rejected`, with their Task 5 numbers), a hash-chained append-only ledger and global trial counter (alpha for a batch = 0.05 / all trials including the batch, so 0.005 for Batch 1, 0.0025 for a 10-idea Batch 2), a batch runner that applies the Task 5 pass rule once per idea and refuses an idea whose rule changed after registration, a daily forward job (idempotent, fresh days only), promotion / retirement / paper-book filters, and a weekly plain-English report. Paper only; no order code; no schedule set up.

Verified: 47 loop tests with hand-computed answers pass (ledger tampering detected; alpha shrinks 0.005 -> 0.0025 -> 0.05/15; refusal after a rule edit; run-once and crash-resume; the rule language reproduces Task 5 ideas 2, 3, 4, 5, 6, 7 trade for trade on the same synthetic data; no lookahead when the future is cut or scrambled; forward log idempotent, and one catch-up run equals day-by-day runs; promotion at exactly 59/60 days, mean exactly 0, p exactly 0.05; retirement at exactly 2x drawdown and a 40-day mean of exactly 0; filters). The 12 other repo test files still pass; `forced_trader_ideas.py` is unedited (code hash 03e3c77355e8 unchanged).
Assumed / not verified: the dev CSVs (`research/data`) are not in this container, so the batch runner and the dry run were exercised on synthetic data only, not yet on the real NIFTY files; the rupee lot value (Rs 15 lakh) and loss limit are placeholders; live Upstox fetching in `daily_forward.py` uses the existing adapter but was not run (no network test, token not touched).
Additions beyond the spec (flagged): promotion also needs >= 20 forward trades; INCONCLUSIVE counts as not surviving (closed as rejected); a changed threshold must be registered as a new idea with `--allow-variant` and counts as a new trial.
