# NIFTY range-forecasting research harness (Kite data)

Autoresearch-style loop, with guardrails against overfitting a short, noisy series.
Target: next-bar `log(high/low)` (volatility proxy), not direction.

```bash
pip install -r requirements.txt
export KITE_API_KEY=... KITE_ACCESS_TOKEN=...      # token expires daily
python fetch_data.py --years 8 --holdout-months 6  # or --synthetic for a dry run
python evaluate.py                                 # what the agent loops on (see program.md)
python final_holdout.py --confirm                  # human, once, at the end
```

Guardrails
- **Hidden holdout:** written to `~/.nifty_holdout` (override with `HOLDOUT_DIR`), outside the repo. Only `final_holdout.py` reads it, and it locks after one run. This is a convention plus a lock file, not a sandbox: run the agent where it cannot read your home directory if you need it airtight.
- **Baselines:** random walk, 20-bar mean, EWMA. A candidate must beat the best one by >= 2% MAE.
- **Walk-forward:** one forecast per origin using only history up to that bar.
- **Trial penalty:** every distinct `candidate.py` evaluated is logged in `ledger.jsonl`; the block-bootstrap bound uses alpha = 0.05 / n_trials.
- **Intraday:** `fetch_data.py --interval 15minute` etc. gives far more samples (Kite caps the span per request; handled).

Not included: transaction costs (irrelevant to a forecasting metric; add them if you turn forecasts into a trading metric) and any TimesFM adapter. I could not verify the TimesFM-3 model name or weights, so plug one into `candidate.py` only after checking they exist.

## TimesFM-3 candidate (optional)
TimesFM-3 exists (Google Research, Aug 2026; `google/timesfm-3.0-pytorch`, 330M params, point + 9 quantiles, optional covariates).
```bash
git clone https://github.com/google-research/timesfm && pip install -e "timesfm[torch]"   # provides `timesfm3`
cp candidate_timesfm.py candidate.py && python evaluate.py --step 5                        # CPU is slow; use --step to thin origins
```
- Set `USE_COVARIATES = True` in the file to feed |return| and volume as past-only covariates.
- The adapter's plumbing is tested with a stand-in model (`python tests/test_timesfm_adapter.py`); it has **not** been run with the real weights, which this sandbox cannot download.
- **License:** the 3.0 weights are non-commercial / non-production. Fine for personal research; check before using forecasts in anything commercial.
