# research/qa: data quality and result checks

| File | What it does |
|---|---|
| `data_quality.py` | Report-only checks (never deletes) on index bars, daily bars, India VIX, expiry calendar; `--options` adds the expired-option files. |
| `repro_daily_mae.py` | Recomputes the daily range-forecast MAE numbers with plain numpy, without the harness, to catch harness bugs. |
| `review_daily_lab.py` | The pre-registered adversarial review of the daily lab (lookahead tests, placebos, 3-chunk stability). Does not touch the trial ledger. |
| `tests/` | Offline tests; run each with `python research/qa/tests/<file>.py`. |
| `data_quality_report.txt`, `daily_lab_review.json` | Saved outputs of the last run (2026-10-18). |

Dev data only. These scripts never read `~/.nifty_holdout`.
