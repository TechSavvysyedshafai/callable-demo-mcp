# Research program (autoresearch-style)

Goal: lower out-of-sample MAE of next-bar `log(high/low)` for NIFTY 50.

Rules
1. Edit ONLY `candidate.py`. Never edit `harness.py`, `evaluate.py`, `kite_data.py` or `final_holdout.py`.
2. Run `python evaluate.py`. Keep a change only if the verdict is `PASS`
   (>=2% better than the best baseline AND the trial-adjusted bootstrap bound is > 0).
3. Every distinct version of `candidate.py` you evaluate counts as a trial and makes the bar
   stricter (Bonferroni). Prefer few, well-motivated experiments over a sweep.
4. Use only the `history` argument inside `predict`. Do not read files, the network, or `~/.nifty_holdout`.
5. Do not try to predict direction; this harness is for range/volatility.

## Scalping variant (`scalp/`)
Same rules, but edit only `scalp/strategy.py` (signal + `ENGINE` exits) and run `python scalp/evaluate.py`.
A change counts only on `PASS`: net profit after costs, >= 200 trades, and a trial-adjusted win over random entries.
