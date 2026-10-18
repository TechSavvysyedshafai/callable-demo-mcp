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
