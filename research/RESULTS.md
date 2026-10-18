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
