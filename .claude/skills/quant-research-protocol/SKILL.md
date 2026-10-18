---
name: quant-research-protocol
description: Use before testing any trading idea or model. Enforces pre-registration, trial counting, controls (random entry, placebo), multiple-testing discipline and stop rules, so a lucky result is not mistaken for an edge.
---

# Quant research protocol

## Before running anything (write this in `research/RESULTS.md` under "Planned")
1. **Hypothesis and mechanism** - one sentence each. "Who loses on the other side and why?" If you cannot answer, stop.
2. **Target and metric** - prefer volatility/range over direction (direction is near a coin flip; range is persistent). State the metric (MAE of log range, net Rs after costs, ...).
3. **Data window** - dev data only. Never the holdout. State dates.
4. **Max trials** - the number of strategy versions you will test, decided now. Each distinct `strategy.py`/`candidate.py` hash counts (see `ledger.jsonl`).
5. **Pass criteria** - numbers fixed in advance (minimum trades >= 200, net > 0 after costs, p vs random entries below 0.05 / n_trials, effect larger than the cost hurdle).

## Controls that must exist for every test
- **Random-entry control** under identical exits and costs (already in the harnesses: `null_pvalue`). A strategy that does not beat random is noise.
- **Placebo / sign flip**: reverse the signal, or shuffle its timing. A real signal should degrade; if the placebo "works" too, the effect is the exit rules or the data, not the signal.
- **Cost sweep**: re-run at several slippage levels. An edge that disappears at a plausible spread is not an edge.
- **Subperiod stability**: split the dev window in halves/thirds; a real effect is not concentrated in one stretch.

## Discipline
- One run per pre-registered idea. If you change anything after seeing a result, it is a **new trial**; log it as such.
- Do not tune thresholds, lookbacks, stops or targets on the dev set and then claim the best setting. A parameter sweep is many trials.
- Prefer few, simple, mechanism-based rules over many features. Complexity budget: every free parameter must be justified.
- Report effect size and uncertainty, not just p-values. With about 500 sessions, only large effects can be detected; say so.
- **Stop rules**: stop and report at the first of: trial cap reached, criteria met, criteria clearly failed. Do not "just try one more".

## After running
Fill in the result next to the plan (same entry), including failures. Then use the `adversarial-review` skill. Only then tell the owner.
