---
name: signal-and-model-development
description: Use when designing a trading signal, forecasting model or feature, or when plugging in a model such as TimesFM-3. Covers baselines first, leak-free features, targets, complexity limits and the repo's strategy/candidate interfaces.
---

# Signal and model development

## Order of work
1. **Baseline first.** Write the simplest model that could work (trailing average, EWMA, HAR for range; no-trade). Anything fancier must beat it by a pre-set margin (>= 2% MAE; see `research/harness.py`).
2. **Choose a forecastable target.** Next-bar range / realized volatility / quantiles are predictable; next-bar direction almost never is. A volatility forecast is useful for sizing, filtering days where expected range < costs, and strike/expiry choice.
3. **Features only from information available at time t.** For intraday signals use only bars up to the latest *closed* bar; the fill is the NEXT bar. Never use the current bar's high/low/close to trade its open. Check every feature for lookahead by shifting it one bar and seeing whether the result collapses.
4. **Walk-forward only.** Fit on the past, predict the future, roll. No random train/test splits on time series.
5. **Complexity budget.** Count free parameters. With ~500 sessions you can support only a handful. Prefer a mechanism over a pattern.

## Repo interfaces
- Daily/range lab: edit only `research/candidate.py` (`predict(history) -> {"mean", "q"}`); evaluate with `research/evaluate.py`.
- Scalp signal: edit only `research/scalp/strategy.py` (`on_bar(o,h,l,c) -> +1/-1/0`, plus `ENGINE` and `OPTIONS` exit settings).
- TimesFM-3: `research/candidate_timesfm.py` (copy over `candidate.py`). Facts: weights `google/timesfm-3.0-pytorch`, 330M parameters, zero-shot,
  point + 9 quantiles, optional covariates; **weights are non-commercial licence**; needs `timesfm` >= 3.0.2 (`import timesfm3`) and a GPU for speed (Colab).
  Run it as ONE pre-registered trial. Do not search covariate combinations.

## Things that look like signals but are not
Momentum/mean-reversion on a single index after costs; patterns found by scanning many indicators; anything whose gross edge is smaller than the round-trip cost
(futures about 15 index points; ATM option about 1.2 premium points plus spread). Compute the cost hurdle first and ask whether the signal's gross move can plausibly exceed it.
