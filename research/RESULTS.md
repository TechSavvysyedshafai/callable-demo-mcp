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


## Planned (pre-registered 2026-10-18, branch claude/employee-settlement; Task 7, Batch 3 "settlement mechanics"; written BEFORE any option candle was downloaded or any G0/T1/T2/T3 number was computed)
Study text: `docs/ideas/IDEAS_BATCH3_SETTLEMENT_2026-10-18.md` (committed before this entry; not edited). Exactly 3 trials (T1, T2, T3), global alpha = 0.05 / 13 = 0.00385 (10 earlier trials in the loop ledger + 3). No variants, no tuning.
Only index data (5-minute bars, daily bars, VIX, expiry calendar) was downloaded before this entry; no statistic was looked at. Data: dev only (to 2026-04-16). The hidden holdout is not read (the fetch script wrote it to `~/.nifty_holdout`; no research code opens it).

**Literal readings of ambiguous rules (fixed now, before running; the owner is told in the report):**
1. *Population:* every expiry in `nifty_expiries.csv` with date from 2024-10-03 to 2026-04-16 inclusive (81). The file also lists 2026-04-21, which is after the dev cutoff; it is not used. Every skipped expiry is listed with a reason.
2. *G0:* uses every dev expiry that has the 15:00 bar, the 15:25 bar and a daily bar (no option data needed). A = daily close from `nifty_day_dev.csv` (assumed to equal the official NSE close = the expiry settlement price), S0 = OPEN of the 15:00 five-minute bar, S1 = CLOSE of the 15:25 bar. Ratio = sample std (ddof 1) of (A - S0) over sample std of (S1 - S0). Gate: STOP the batch if ratio > 0.85.
3. *Strike:* K = S0 rounded to the nearest 50, halves rounded up (floor(S0/50 + 0.5) * 50). Wings (T2) are K + 100 call and K - 100 put.
4. *Fills:* every leg is traded at the OPEN of its 15:00 bar. Sells fill at open - slippage, buys at open + slippage (floored at 0), slippage per leg 0.10 / 0.20 / 0.30 (0.20 is the decision value). A leg with no 15:00 candle (or an open <= 0) means that expiry is skipped for that trial (reason "missing_candle").
5. *Costs:* `OptionCostModel.side()` for every entry order (Rs20 brokerage each, STT 0.15% on SELL premium, exchange, stamp on buys, GST). Positions are held to settlement, so no exit order and no exit brokerage; settlement STT = 0.15% x intrinsic x 75 on EVERY in-the-money leg, long and short (the conservative rule used in `research/selling`). Lot = 75 for the whole window (as instructed; unverified).
6. *Settlement value:* intrinsic value against A (call: max(A - K, 0); put: max(K - A, 0)).
7. *Net per trade (Rs)* = (points P&L x 75) - entry fees - settlement STT. "Mean before costs" = points P&L x 75 at ZERO slippage and zero fees.
8. *Pass test:* verdict as in the repo (`forced_trader_ideas.verdict`, with alpha 0.00385 and n >= 60): SURVIVES if mean net at 0.20 > 0 AND bootstrap p < 0.00385 AND n >= 60 AND both halves positive; INCONCLUSIVE if mean net > 0 and p < 0.00385 but another condition fails; otherwise REJECT. Bootstrap p = `forced_trader_ideas.bootstrap_p` (moving blocks of 5 chronological trades, 10,000 resamples, seed 20261018, one-sided) on net Rs per trade at slippage 0.20. Halves = split at the calendar midpoint between the first and last traded expiry (same as `fi.halves`). The brief's "random-entry style code" is used only in T3 (random strike). The brief's pass rules for T1/T2 list no random-entry test, so none is a pass condition.
9. *Calibration ratio (T1; reported, not a pass condition):* straddle price = open of the 15:00 call bar + open of the 15:00 put bar (no slippage). Model value = (1/sqrt(3)) x sigma_pts x sqrt(6), the literal "0.58 x sigma x sqrt(T)"; sigma_pts = sample std of the day's 5-minute close-to-close changes in index points (bars 09:15 up to the 14:55 bar, whose close is the 15:00 price), T = 6 bars (15:00-15:30). Primary ratio = mean(straddle price) / mean(model value) over the T1 days. Note: 0.58 x sigma x sqrt(T) is the standard deviation of A - S0, not a straddle value; a zero-mean normal straddle is worth sqrt(2/pi) = 0.798 times that. So I ALSO print the ratio against 0.798 x that value, labelled as such; only the first is "the" calibration ratio.
10. *T3:* uses expiry days with the 14:50 bar's OI for at least 3 complete CE+PE strike pairs among the strikes within +/-500 points of K0 (K0 = S0 rounded as in 3), 21 strikes at most. "At 14:55" is read as the last COMPLETED bar at 14:55 = the bar labelled 14:50 (the bar labelled 14:55 closes at 15:00, so using it would look ahead); for each strike and side the OI is the last OI at or before the 14:50 bar. Total OI = CE + PE; only strikes where BOTH sides have OI count. Max-OI ties go to the lowest strike. Statistic = mean over days of |A - K_maxOI|. Null = the same statistic with K drawn uniformly (with replacement across draws, independently each day) from that day's strike set; 10,000 draws per day = 10,000 replicate means. One-sided p = (1 + #{null mean <= observed mean}) / 10,001, seed 20261018. Pass: p < 0.00385. (No n requirement stated; small n is reported.) Known weakness, NOT fixed (no variants): the strike set is centred on spot, and high-OI strikes tend to be near the money, so a "closer than random" result can come from nearness to spot alone rather than from pinning. The adversarial review prints the distance of the spot-nearest strike as a descriptive yardstick; it is not a trial.
11. *Data checks:* option files hold 5-minute candles with OI for the expiry day only; the downloader asks Upstox's expired-contract list for each expiry; every expiry whose contract list or candles come back empty is counted as skipped. Special sessions (Muhurat etc.) are not expiries in this window; 2025-04-30 and 2025-05-08 have two extra bars after 15:25 (15:35, 15:55) in the Upstox file: they are ignored (nothing after 15:25 is used).
12. *Lookahead rule:* decisions use only candles labelled <= 15:00 (T1/T2: the 15:00 bar's open, T3: 14:50 bar); settlement uses only the daily close.


## 2026-10-18: Task 7 results. Batch 3 "settlement mechanics" (branch claude/employee-settlement). Trials 11-13 of 13; alpha 0.05/13 = 0.00385
**Answer first:** selling the last-30-minutes straddle on NIFTY expiry days does NOT make money after costs. T1 (short straddle) and T2 (with 100-point wings) are both **REJECT**. The averaging effect is real in the index (G0 ratio 0.68), but the options already price it: the straddle sells for about 1.13x what the "averaged" model says it is worth, and that is not enough to pay Rs53 (T1) / Rs101 (T2) of fees plus slippage. T3 (pin test) passes its written test (p = 0.0001) but only because high-open-interest strikes sit near the index; the strike nearest the index at 15:00 is even closer to the settlement (24 pts) than the max-OI strike (43 pts). So T3 is a statistical pass with **no tradable edge** (see review). Nothing goes to forward paper from this batch.

Data: dev only (to 2026-04-16), Upstox, downloaded 2026-10-18 (expiry-day 5-minute candles incl. OI, strikes K0 +/-500; 81 expiries x 42 contracts; 46 contracts not available: all 42 of 2024-12-26, 2 of 2025-03-27, 1 each of 2025-06-26 and 2025-09-30). Holdout not read.
Skipped: **1 expiry (2024-12-26: Upstox returns no candles for any contract)** in T1, T2 (missing_option_file) and T3 (fewer than 3 complete strike pairs). n = 80 of 81 everywhere. G0 used all 81.

| | n | net/trade Rs @0.10 / 0.20 / 0.30 | before costs (mid, no fees) | boot p (0.20) | halves (1st / 2nd) | worst trade | max drawdown | calibration | verdict |
|---|---|---|---|---|---|---|---|---|---|
| G0 | 81 | std(A-S0)=34.2, std(S1-S0)=50.2, ratio **0.680** (stop > 0.85) | | | | | | | PASS (continue) |
| T1 short straddle | 80 | -37 / **-52** / -67 | +32 | 0.545 | +227 / -317 | -7,511 | -19,889 | 1.13 (1.42 with the sqrt(2/pi) factor) | **REJECT** |
| T2 + wings | 80 | -157 / **-187** / -217 | -26 | 0.835 | +161 / -518 | -5,082 | -26,386 | same | **REJECT** |
| T3 pin | 80 | no trading: mean distance of max-OI strike to settlement 43.4 pts vs 263.2 for a random strike; spot-nearest strike 24.2 | | p = 0.0001 | | | | | passes the written rule; **no edge** (review) |

Details: T1 total net Rs -4,133 over 80 days at 0.20 (fees Rs53 per trade); win rate 62.5% but the loses are large (5 worst: -7,511 on 2024-12-05, -4,893 on 2025-07-31, -4,714 on 2025-10-28...). Halves split at 2025-07-08. Bootstrap p at 0.10/0.30: T1 0.514/0.579, T2 0.788/0.872. Before-costs mean is not significant either (p 0.36, 0.50). Calibration: mean straddle price Rs24.6 vs model 21.8 (literal 0.58 x sigma x sqrt(T)); daily ratio mean 1.16, median 1.15. T3: max-OI strike is the spot strike on 61% of days; settlement within 25 points of it on 49% of days; 1 tie; 21 strikes per day.

**Verified vs assumed.** Verified: code vs an independent csv-only recomputation (`settlement_crosscheck.py`): every T1/T2 day agrees to Rs0.000000000, T3 distances agree, own Monte Carlo p = 0.0001; hand-computed payoff/fee/Asian tests (19); all 17 other test files in the repo pass; global trial counter in the hash-chained loop ledger is 13 (verify() ok, 24 lines). Verified from Upstox contract lists: lot sizes were **25 (14 expiries to 2024-11-14), 75 (52, to 2025-12-23), 65 (15, from 2025-12-30)**; the brief's 75 was used for all days. Assumed: daily close in `nifty_day_dev.csv` equals the official NSE close = settlement price (the G0 ratio of 0.68 supports it being an average, not the last print); Rs20 brokerage (Basic plan), STT 0.15% on sells and on settled intrinsic value (the 0.15% applies from 1 Apr 2026, earlier rates were lower, so costs are overstated for most of the window); slippage (candles have no bid/ask); the Upstox candle at 15:00 is a tradable price in these illiquid expiry-day contracts; special sessions: none fall on an expiry in the window; 2025-04-30 and 2025-05-08 carry two extra post-close bars that are ignored; the expiry calendar is Upstox's (Thursday until 2025-08-28, Tuesday from 2025-09-02, with holiday shifts, as listed). The SEBI circular was not read.

**Deviations / readings:** all readings written before running (RESULTS.md "Planned" above). The most consequential: calibration ratio uses the literal 0.58 x sigma x sqrt(T) (a standard deviation, not a straddle value), with the 0.798 version shown beside it; T3 reads "14:55" as the 14:50 bar (last completed) and counts only strikes with both CE and PE OI. Lot 75 for all days although the real lot was 25 / 65 for 29 of 81 expiries: T1 net by lot era at 0.20 is +593 (n=7, lot 25 era), -142 (57), -11 (16) if the rupee amounts are read as given for 75 units; scale to the actual lot to get true rupees. No pass or fail flips from this (the full-sample sign is negative at every slippage).

**Adversarial review** (skill `adversarial-review`)
1. Lookahead: tests scramble all option and index candles after 15:00 and the trade is unchanged; sigma uses bars before 15:00 only; T3 uses the 14:50 bar and a test proves an OI that appears at 14:55 is ignored. Settlement uses only the daily close.
2. Leakage: dev files only (index file ends 2026-04-16); 2026-04-21 expiry excluded; no code opens the holdout (test greps source).
3. Trials: exactly 3, run once; the only change after the pre-registration commit was none to rules. Counter 13.
4. Controls: no random-entry or placebo control exists for T1/T2 (not in the brief, and extra variants are forbidden). T3 has the random-strike control and it passes, but see item 10.
5. Costs: fees per order, 4 orders for T2, settlement STT on both legs; result is negative even at 0.10 slippage, and before costs T1 is only +Rs32 (p 0.36), so costs are not what decides it: there is no edge to pay them from.
6. Fills: fill at the open of the 15:00 candle in thin expiry-day options; real spreads are probably wider than Rs0.30, so reality is worse.
7. Selection: only 2024-12-26 skipped; no strikes dropped.
8. Regime: the first half is positive (+227), the second negative (-317); 5 days carry most of the losses; the lot size and STT rate changed inside the window.
9. Arithmetic: reproduced independently, see above.
10. Plausibility of T3: NOT a pin edge. The strike set is centred on spot and max-OI strikes are near spot, so beating a uniform random strike is almost automatic; the spot-nearest strike (24.2 pts) beats the max-OI strike (43.4 pts), i.e. OI adds nothing beyond "stay near the index". Also the 49% "within 25 points" is about the 50 point strike spacing and the 21-strike window.
**Verdicts:** G0 PASS. **T1 REJECT. T2 REJECT. T3: passes the written rule (ledger records it as SURVIVES) but REJECT as evidence of a pin edge.** Gate step reached: none beyond step 1. The ledger says "SURVIVES" for B3-03 only because the written rule was mechanical; the loop must not send it to forward paper (there is nothing to trade).
**Next single step (owner):** none for this idea. If settlement averaging is still of interest, record live bid/ask on expiry afternoons for several weeks; only real spreads can show whether selling is cheaper than the Rs53+ fee drag.

## 2026-10-18: Task 9a, gold wheel on MCX: feasibility only (branch claude/employee-goldfeas). No trial, no backtest, no P&L. Trial counter unchanged.
**Verdict: NOT FEASIBLE as a backtest.** Full report: `research/goldwheel/FEASIBILITY.md`; probe files in `research/goldwheel/feasibility/`.
- Smallest MCX gold contract with options: **Gold Mini (GOLDM), 100 g** (Upstox lot 100, Rs 10 per Re 1). Options also exist on Gold 1 kg. **Gold Guinea, Petal and Ten have no options.** Options are European, on futures, devolve into the futures (physical-delivery risk if held), Rs 500 strikes, **monthly only** (no weeklies). Listed expiries 2026-10-29, 11-27, 12-29 (Upstox; Dhan shows one day earlier, unresolved).
- Upstox expired-instrument APIs return **nothing for MCX** (docs: "Expiries is currently not available for the MCX"; real calls: empty lists). Active-contract candles (5-minute and daily, with OI) work but start only when a series is listed, about 4 weeks before expiry; oldest option candle seen 2026-09-28. **Cycles in dev data (to 2026-04-16): 0.**
- Costs read from Zerodha's charges page 2026-10-18 (Upstox commodity row not readable): MCX option txn 0.0418% of premium, futures 0.0021%; CTT futures 0.01% sell, options 0.05% sell on premium; stamp 0.003% / 0.002% buy; GST 18%; SEBI Rs 10/crore; brokerage Rs 20 per order (assumed for Upstox). Not verified: CTT on exercised options, any Budget 2026 CTT change, MCX delivery-period margin, Gold Mini option expiry rule.
- Monthly cycles mean about 12 a year; even a perfect source would give few cycles. Next single step (owner): decide whether to record live GOLDM option quotes for forward paper only, or drop the idea.
**Verified vs assumed:** see section 7 of FEASIBILITY.md. Holdout not read. I saw some current gold price levels in probe output; nothing was computed from them.

## Planned (pre-registered 2026-10-18, branch claude/employee-wheel; Task 8, Batch 4 "wheel on a NIFTY index proxy"; written BEFORE any option candle was downloaded or any wheel/benchmark number was computed)
Study text: `docs/ideas/IDEAS_BATCH4_WHEEL_2026-10-18.md` (committed earlier; not edited). Exactly ONE trial (the wheel vs buy-and-hold, primary test) plus the three listed controls (not trials). Global alpha = 0.05 / 14 = 0.003571 (13 earlier trials in the loop ledger + this one). No variants, no tuning.
Only index data (5-minute bars, daily bars, VIX) and the expiry calendar were downloaded before this entry (the calendar's dates were looked at; no price statistic was). Dev data only (to 2026-04-16); the fetch script wrote the hidden holdout to `~/.nifty_holdout` and no research code opens it.

**Literal readings of ambiguous rules (fixed now, before running; the owner is told in the report):**
1. *Population:* every expiry in `nifty_expiries.csv` from 2024-10-03 to 2026-04-16 inclusive (81; the last is 2026-04-13; 2026-04-21 is after the cutoff and unused). "Week k" = the interval from the official close of expiry k-1 to the official close of expiry k (week 0: from the close of the first entry bar to the close of 2024-10-03). Official close = daily close in `nifty_day_dev.csv` (assumed equal to the NSE close and the settlement price).
2. **TIMING CONFLICT (the one real deviation from "same entry rule as selling"):** the selling rule enters on the trading day nearest on or before expiry-7 days. For a normal 7-day week that is the PREVIOUS expiry's own day, 09:30, six hours BEFORE the previous contract settles (15:30). The wheel needs that settlement to know whether it is in state CASH (sell a put) or LONG (sell a call). Using it would be lookahead. Reading used: **entry day = the LATER of (a) the selling-rule day and (b) the first trading day strictly after the previous expiry's day** (week 0: (a)). So weeks after a 7-day gap enter the morning after the previous expiry; weeks after an 8-day gap are unchanged. Entry bar = first 5-minute bar at or after 09:30 on that day. Everything else in the entry rule is unchanged. A lookahead diagnostic using the as-written selling-rule day is run and printed (information only, labelled NOT tradeable, not a trial, not used for the verdict).
3. *Spot, strikes, fill:* spot = close of the entry bar; put strike = floor(spot x 0.988 / 50) x 50, call strike = ceil(spot x 1.012 / 50) x 50 (the `research/selling` helper, with its 9-decimal guard). The call strike is computed from THIS week's entry spot, never from the assignment strike. The short option fills at the OPEN of the entry bar minus slippage (floored at 0). Inherited weakness, not fixed: the strike uses the close of the same bar whose open is the fill (up to 5 minutes of look-ahead in the strike choice, as in `research/selling`); the +1 / +2 bar controls and the adversarial review address it.
4. *Settlement and states:* CASH sells the put, LONG sells the call; held to expiry. Put: assigned iff settle < strike (strict); call: called away iff settle > strike (strict). Equal = nothing happens.
5. *P&L per week (Rs, lot 75):* option premium received (fill x 75) minus option fees (`OptionCostModel.side(fill, 75, is_buy=False)`) minus intrinsic paid ((strike - settle)+ for a put, (settle - strike)+ for a call, x 75) minus settlement STT (`selling` rule: 0.15% x intrinsic x 75 on an in-the-money leg) plus, if LONG at the start of the week, the exposure mark (settle - previous official close) x 75. Assignment: from the settle onward the wheel holds exposure marked at the settle (the put loss is paid as intrinsic, so no extra mark). Called away: the exposure is sold at the call strike; the week's exposure mark and the call intrinsic combine to (call strike - previous close) x 75; the wheel is CASH next week. An assigned put in LONG is impossible (LONG sells calls only).
6. *Exposure costs:* 0.065% of notional at EACH assignment (notional = put strike x 75) and EACH called-away event (call strike x 75), literal reading of "per assignment and per called-away event"; this figure is all-in (STT, exchange, brokerage): no extra Rs20. Conservative: it charges twice what a real assign-then-call-away round trip costs. A wheel still LONG at the end of the sample is liquidated at the last official close with the same 0.065% (to match the benchmark's exit). Benchmark: bought at the close of the first entry bar, sold at the last official close, 0.065% x notional at each end; marked weekly at official closes; week 0 benchmark mark = (settle of 2024-10-03 - first entry spot) x 75.
7. *Skipped weeks:* a week is skipped when its entry bar is missing, or the needed option file (put in CASH, call in LONG) is missing, or has no candle at the entry timestamp, or the fill is <= 0. A skipped week: no option trade, no premium, no assignment or call-away; the state and any exposure are carried and still marked at official closes. D_t is computed for all 81 weeks including skipped ones (the wheel sat out while the benchmark moved), so no week is dropped from the comparison. Every skipped week is listed with a reason. For the controls the needed leg is their own (put for control 1, call for control 2).
8. *Primary test:* D_t = wheel week net P&L - benchmark week net P&L (Rs per lot-of-75), t = 0..80, at slippage 0.20. One-sided bootstrap p for mean(D) > 0 = `forced_trader_ideas.bootstrap_p` (moving blocks of 5, 10,000 resamples, seed 20261018, centred). Pass (all four): mean D > 0 at 0.20; p < 0.003571; max drawdown of the wheel smaller in size than the benchmark's (`bt.max_drawdown` of the cumulative weekly net P&L starting at 0); mean D > 0 in BOTH halves (weeks split at the calendar midpoint between the first and last expiry date; expiry <= midpoint = first half). SURVIVES if all four; INCONCLUSIVE if mean D > 0 and p < alpha but a different condition fails; otherwise REJECT.
9. *Information only:* total return = total net P&L / (first entry spot x 75); mean, median, worst week, best week; max drawdown; Sharpe-like = mean / sample std (ddof 1) of the weekly net P&L (not annualised); weeks spent CASH vs LONG (state at the start of the week); number of assignments and call-aways; premium collected (after slippage) vs intrinsic paid vs exposure marks vs fees; idle-cash information: 6.5% a year x (calendar days of the week / 365) x (first entry spot x 75) credited for each week that starts in CASH (the benchmark is never idle); lot-size eras from the Upstox contract list (75 is used everywhere; real lots were 25 / 75 / 65 in Task 7's window; unverified for this one).
10. *Controls (not trials; same fills, costs and skip rule):* (1) short-put-only: every week sell the put, assignment only costs the intrinsic (no exposure, no exposure costs), always CASH; (2) covered-call-only: always LONG from the benchmark entry (entry/exit 0.065% as the benchmark), every week sell the call; a called-away call just pays its intrinsic and the exposure is kept (cash-settled), no re-buy cost; (3) the wheel with the entry bar shifted +1 and +2 bars (benchmark entry also shifted). Each is shown as mean D vs the same benchmark, bootstrap p (information only), and the wheel's gain over control 1 as the "does the call overlay help" number.
11. *Slippage:* 0.10 / 0.20 / 0.30 per option fill, rerun in full. The state path does not depend on slippage (strikes and settles do not).
12. *Lookahead rule (tested):* the state used to choose the leg at entry depends only on settlements dated BEFORE the entry day; the entry spot and the fill come from candles labelled at or before the entry timestamp; settle comes only from the daily close. Option files hold the expiry week's candles (expiry-9 days to expiry).
13. *Download:* `research/selling/download_needed.py` fetches condor legs (with 150-point wings) at the selling entry day only, so it is not run as is. `research/wheel/wheel_download.py` reuses its method and helpers (contract list per expiry, strikes from the entry-bar close, same file names, resumable, Upstox throttle) for the put and the call only, over the entry spots of: both timings (reading 2 and the as-written diagnostic) at shifts 0, +1, +2. This is a superset of what the state machine needs.


## 2026-10-18: Task 8 results. Batch 4 "wheel on a NIFTY index proxy" (branch claude/employee-wheel). Trial 14 of 14; alpha 0.05/14 = 0.003571
**Answer first: REJECT under the pre-registered rule.** In this 81-week window the wheel did beat buy-and-hold (Rs +3,647 a week better on average, better in both halves, smaller drawdown), but the evidence is not strong enough: bootstrap p = 0.0116, and the bar after 14 trials is 0.0036. The edge that is there is mostly "the wheel owns only about 60% of the index and the index fell 8%": it gave back the big rebounds and lost Rs 1.5 lakh in the four-week March 2026 sell-off while holding the exposure. Nothing goes to forward paper.

Data: dev only (to 2026-04-16), Upstox, downloaded 2026-10-18: 394 of 400 wanted weekly put/call contracts (5-minute candles). 81 weeks (2024-10-03 to 2026-04-13). Holdout not read.
**Skipped weeks: 2 of 81** (both in state LONG, both counted in D with the wheel doing no option trade): 2024-12-26 (Upstox has no candles for any contract that week: the same hole as in Tasks 3 and 7) and 2024-11-07 (the entry fell on the Diwali Muhurat evening session, 2024-11-01 18:00, and the call's candle has no bar stamped 18:00: `no_candle_at_entry`). Another entry (week of 2025-10-28) was on the Muhurat session of 2025-10-21 at 13:45 and was traded. This came from the literal "first trading day after the previous expiry" and was found in review; the rule was NOT changed afterwards.

| Primary, slippage 0.20 | Wheel | Buy-and-hold |
|---|---|---|
| Total net (Rs, 75 units) | **+128,735** (+6.6% of Rs 19.5 lakh notional) | **-166,685** (-8.5%) |
| Mean / median per week | +1,589 / +2,009 | -2,058 / -5,220 |
| Worst / best week | -45,793 / +75,448 | -63,821 / +108,938 |
| Max drawdown | -191,696 | -288,547 |
| Sharpe-like (mean/std, weekly) | 0.068 | -0.062 |

**Primary test (D = wheel - benchmark, per week):** mean D **+3,647**, median +3,727, worst -53,566, best +40,593; bootstrap p (blocks of 5, 10,000, one-sided) **0.0116** vs 0.003571 -> fails. Halves (split 2025-07-08): +2,760 (40 weeks) / +4,513 (41 weeks), both positive. Wheel max drawdown smaller (-191,696 vs -288,547). Conditions: a mean D>0 PASS; b p<alpha **FAIL**; c smaller drawdown PASS; d both halves PASS. Verdict by the written rule: **REJECT**. Slippage sweep: mean D +3,654 / +3,647 / +3,640 and p 0.0116 / 0.0116 / 0.0116 at 0.10 / 0.20 / 0.30 (slippage barely matters: fees and slippage together are about Rs 3,000 on 360,000 of premium).
Information only: weeks starting CASH 31 / LONG 50; 9 assignments, 8 called away; premium collected +359,848, intrinsic paid -300,037, exposure marks +93,236, option fees -2,555, settlement STT -450, exposure costs -21,306. Idle cash at 6.5% would add about +74,755 on the 31 CASH weeks (wheel total +203,490, 10.4%); the benchmark has no idle cash.

**Controls (not trials; vs the same benchmark, slippage 0.20):**
| | total net | mean D | boot p | halves | max DD |
|---|---|---|---|---|---|
| 1 short-put-only | +21,811 | +2,327 | 0.232 | +2,493 / +2,165 | -85,896 |
| 2 covered-call-only (always LONG) | -51,804 | +1,418 | 0.063 | -265 / +3,061 | -225,043 |
| 3a wheel, entry +1 bar | +114,645 | +3,488 | 0.0105 | +2,356 / +4,592 | -188,283 |
| 3b wheel, entry +2 bars | +100,190 | +3,293 | 0.0131 | +2,242 / +4,319 | -198,353 |
Does the call overlay help? Versus put-only the wheel is +106,924 better in total but its worst drawdown is more than twice as deep (-191,696 vs -85,896): the overlay adds return only because the wheel holds the index after an assignment. Put-only is very quiet (p 0.23, 17 assignments, each paid in cash); covered-call-only barely beats the benchmark. Entry shifted 1 or 2 bars changes mean D by 4% and 10%, so the 5-minute choice of entry bar is not driving the result.

**Verified vs assumed.** Verified: the independent plain-CSV recomputation (`research/wheel/wheel_crosscheck.py`, shares no code) agrees with the engine for the wheel, put-only, call-only and the benchmark for every one of the 81 weeks to Rs 0.000000000; 20 hand-computed tests (assigned / called away / stays CASH / stays LONG, settle exactly on the strike, payoff signs, exposure marks, fees, no-lookahead, skipped weeks, benchmark, controls, statistics, ledger); every test file in the repo passes (19 files, 18 existing + this one); the global trial counter in the hash-chained loop ledger is 14 (verify() ok, 26 lines); lot sizes from Upstox's contract lists: 25 (14 expiries), 75 (52), 65 (15). Assumed: lot 75 for every week (so rupee figures are for 75 units, not true lots, and the true ones were 25 early on and 65 now); the daily close equals the official settlement price; Rs 20 brokerage and the 0.15% STT rates apply to the whole window (the 0.15% only began 1 Apr 2026, so option STT is overstated); 0.065% of notional at each assignment and call-away is all-in and applies to an index future that we do not trade (this is an INDEX PROXY, not a real single-stock wheel: cash-settled options, no stock, no dividends, no physical delivery, no margin model); fills at the open of a 5-minute candle minus Rs 0.20 (no bid/ask in the data); 80 weeks contain one 10% fall and cannot show a real crash.

**Deviations / readings (all written before running, see "Planned" above).** The consequential one: the selling entry rule puts the entry on the PREVIOUS expiry's own day at 09:30, before that contract settles, so the wheel could not know whether to sell a put or a call. I used the first trading day AFTER the previous expiry (79 of 81 entry days differ from the selling rule). The as-written timing was run as a lookahead diagnostic only: mean D +2,695, p 0.089, wheel total +51,601 (lower, so the fix did not help the wheel). Downloader: `research/selling/download_needed.py` fetches condor wings at the selling entry day, so a sibling `research/wheel/wheel_download.py` reuses its method for the put and call only. Everything else is the owner's rules as written.

**Adversarial review** (skill `adversarial-review`; `research/wheel/wheel_review.py`, information only)
1. Lookahead: the leg sold in week k depends only on settlements dated before the entry (tested by changing settlement k and checking weeks <= k are unchanged, and by flipping an earlier settlement and seeing the leg change); later bars and later option candles are irrelevant (tested). Inherited weakness: the strike uses the close of the same 5-minute bar whose open is the fill (up to 5 minutes), as in `research/selling`; the +1 / +2 bar controls give about the same answer.
2. Leakage: dev files only (index data ends 2026-04-16); 2026-04-21 expiry excluded; no code opens the holdout (test greps source).
3. Trials: exactly one trial, run once; the second run only added the ledger record (deterministic code). Counter 14.
4. Controls: put-only, covered-call-only, +1 and +2 bars as listed. No random-entry null was pre-registered for this study.
5. Costs: fees and slippage are small next to the P&L (about Rs 3,000 in option fees and STT on 360,000 of premium; exposure costs 21,306 at a deliberately double-counted 0.065% per event). Slippage 0.10 to 0.30 changes nothing.
6. **Exposure, not skill:** regression slope of the wheel's weekly P&L on the benchmark's is 0.595 (correlation 0.85): it holds about 60% of the index and loses less when it falls. D is +12,203 per week when the index fell (48 weeks) and **-8,798 when it rose** (33 weeks). A beta-adjusted gain of Rs +2,813 a week has p 0.0028 (exploratory, post-hoc, no pass rule, not a second trial); it says the wheel collected a little more premium than its lower exposure explains. A real test of that needs a window with a long up-trend and a crash.
7. Start point: the benchmark is bought at the first entry (26,033 on 2024-09-26, near the all-time high) and week 0 contributes D = +28,140; without week 0 mean D is +3,341, p 0.0279.
8. Concentration: 63 of 81 weeks have D>0 but the ten largest-|D| weeks sum to -56,214 (the big rebounds the wheel misses: 2024-12-05, 2025-10-20, 2025-04-17, 2025-05-15, 2025-08-21 are its five worst); wheel dropped Rs 150,692 over weeks 75-78 (March 2026) while LONG.
9. Skipped weeks: two, both listed; excluding them mean D is +3,739.
10. Arithmetic: reproduced independently, see above.
**Verdict: REJECT** (mean D>0, both halves, smaller drawdown, but p 0.0116 > 0.003571). Gate step reached: none beyond step 1; not sent to forward paper.
**Next single step (owner):** none for this idea on this data. If the wheel on a stock you actually hold is of interest, it needs single-stock option history (we have none) and a window that includes a long rally and a crash; 80 weeks of an index cannot supply that.

## Planned (pre-registered 2026-10-19, branch claude/employee-goldsilver; Task 11, Batch 6 "gold vs silver ratio pair trade"; written BEFORE any ratio, Z-score or trade was computed)
Study text: `docs/ideas/IDEAS_BATCH6_GOLD_SILVER_PAIR_2026-10-19.md` (committed earlier; not edited). Exactly ONE trial, **B6-01** (trial 16 overall: 14 in the loop ledger plus Task 10's option study as 15, then this one; alpha = 0.05 / 16 = 0.003125). Plus the listed information-only checks (not trials). No variants, no tuning. I do NOT append to `research/ideas/loop/ledger_loop.jsonl`; the project manager does it after merging. B6-01's numbers go into `research/goldsilver/results/goldsilver_results.json`.
Before this entry only the two daily price files were downloaded and checked for plain data quality (duplicates, gaps, NaN, zero or negative prices, bar shape, largest one-day moves). No ratio, Z-score or P&L was computed. Dev data only: Upstox daily candles, request end date 2026-04-16 and rows after it dropped again in code; the hidden holdout `~/.nifty_holdout` is not read by any code here.
**Instrument keys (found with the Upstox search API on 2026-10-19; keys are not secrets):** GOLDBEES = `NSE_EQ|INF204KB17I5` (Nippon India ETF Gold BeES), SILVERBEES = `NSE_EQ|INF204KC1402` (Nippon India Silver ETF). The public instrument-list host was blocked from this sandbox, so the search API was used. Downloaded 2026-10-19: GOLDBEES 2,792 rows 2015-01-01 to 2026-04-16 (one exact duplicate row on 2015-12-31, outside the overlap; the loader drops it); SILVERBEES 1,038 rows, **first row in the data 2022-02-07** (the study text said "around 2022, unverified"). Every one of the 1,038 SILVERBEES dates is also a GOLDBEES date, so nothing is lost by aligning.

**Literal readings of ambiguous rules (fixed now, before running; the owner is told in the report):**
1. *Calendar:* the common trading days of the two series (dates present in BOTH), 2022-02-07 to 2026-04-16. "Trading day" = a row of that common calendar. A date in one series only, or a row with a missing or non-positive open or close in either, is a **skipped day**: it is counted and reported, and removed from the calendar (the rolling window then spans the remaining rows). I expect zero.
2. *Z-score:* r_t = ln(GOLDBEES close / SILVERBEES close). Z_t = (r_t - mean of the last 60 values of r) / std of the last 60 values of r; the 60 values are rows t-59..t (window ENDS at t and includes t). Std is the **sample standard deviation (ddof = 1)** (the study does not say; this is the usual convention). Z is undefined for the first 59 rows and when std = 0 (no signal then).
3. *Signal and entry:* decided on the close of day t, only when **no position is open at that close**. A position whose exit was triggered at close t is still open at that close (it leaves at the next open), so no new signal is taken on that same close; the earliest new signal is the following close. Entry = **open of day t+1** for both legs. Z >= +2.0: sell GOLDBEES, buy SILVERBEES; Z <= -2.0: buy GOLDBEES, sell SILVERBEES. A signal on the last row of the data has no next open and is a skipped signal (counted). Thresholds are inclusive; ties use a 1e-12 tolerance.
4. *Equal rupee notional* at entry on both legs, never rebalanced. So P&L per trade, as a fraction of ONE leg's notional, = (return of long leg) - (return of short leg), return = exit open / entry open - 1 (simple, not log). One-leg notional is the unit of every number below.
5. *Exits:* the entry day is e (entry at its open). At each close from day e onward (k = 0, 1, ... trading days after e), if |Z| <= 0.5 or |Z| >= 4.0, exit at the **open of the next day**. Time stop: if no such close happened through day e+19 (the 20th held day), exit at the open of day e+20. So the longest hold is 20 trading days (open to open); the shortest is 1. If the data ends before the exit open exists, the trade is **unfinished**: dropped from the statistics and reported. A signal can have |Z| >= 4.0 on the signal day itself; it still enters (the rule says Z >= 2) and the stop then fires at the close of day e. Written so it is not a surprise.
6. *Costs:* round trip 0.10% of notional per leg = **0.20% of one-leg notional per trade**. Financing/borrow drag = **0.02% per CALENDAR day held** (exit date minus entry date, weekends included) on the short leg's notional (= one-leg notional). Calendar days chosen because the study says "per day held" without "trading" and money costs accrue on weekends; this is the harsher reading. The trading-day reading is reported as information only. Net per trade = gross - 0.002 - 0.0002 x calendar days.
7. *Bootstrap:* `forced_trader_ideas.bootstrap_p` (imported, not edited), blocks of 3 trades, 10,000 resamples, seed 20261018, one-sided, on the chronological per-trade nets.
8. *Random-date null:* same number of trades, same holding days (trading-day rows, trade by trade), same long/short mix, 10,000 draws, seed 20261018. For each holding length h the candidates are every possible entry row from the first row on which a real signal could have entered (row 60 of the common calendar, the first day after the first possible Z) to the last row with an exit open; each candidate carries its own calendar-day financing. Same draw method as `forced_trader_ideas.null_p` (distinct random starts per hold length, first n_long of them long-gold-short-silver, rest the reverse). `null_p` itself charges one scalar cost, so I wrote `gs_null_p` with the identical draw logic but a per-candidate cost, and a test checks it equals `null_p` when financing is zero. p = (1 + number of draws with mean net >= observed) / (10,000 + 1).
9. *Halves:* split at the calendar midpoint of the sample span (first to last common date); a trade belongs to the first half if its ENTRY date is on or before the midpoint. The midpoint of the tradable span (first possible entry to last date) is reported as information only.
10. *Pass (all, as written):* trades >= 15; mean net per trade > 0; bootstrap p < 0.003125; mean net positive in each half; random-null p < 0.003125. If trades < 15: **INCONCLUSIVE** whatever the mean. If trades >= 15 and any other condition fails: REJECT.
11. *Information only (not trials):* zero-cost result (cost 0 and financing 0); each half separately; lookbacks 40 / 60 / 90 x entry thresholds 1.5 / 2.0 / 2.5 (9 cells, exit 0.5, stop 4.0 and the 20-day stop unchanged; the 60 / 2.0 cell must equal B6-01 exactly, a test checks it); trading-day financing reading; max drawdown (peak-to-trough of the running sum of per-trade nets, in % of one-leg notional); worst and best trade. **Plateau vs spike rule fixed now:** the base cell is on a plateau if at least 6 of its 8 neighbours have the same sign of mean net as the base cell AND no neighbour with 15 or more trades has a bootstrap p below 0.003125 while the base has not (a neighbour that "works" while the base does not would mean the base was the unlucky one, which is also reported); otherwise it is a spike. Cells with fewer than 15 trades are flagged but still counted for the sign.
12. *Lookahead rule (tested):* Z at day t uses rows <= t only (changing any later price leaves every earlier Z unchanged); the entry price is the open of the NEXT row; exit prices are the opens of rows after the trigger close.
13. *Assumptions stated up front:* the ETFs are a PROXY for the metals; the tradable short leg would be an MCX future (no history here), and ETF premium/discount to NAV, futures carry and roll are not modelled. Shorting an ETF cash position is not possible for a retail account in India intraday-carried; this is a modelling stand-in. The financing drag is an assumption, unverified. The 0.10% per leg cost is the study's "harsh" figure, not a verified broker quote.
14. *Checks planned:* hand-computed unit tests, an independent plain-CSV crosscheck script that shares no code with the engine, a hostile review (`adversarial-review` skill), and every existing test file in the repo run before and after.
