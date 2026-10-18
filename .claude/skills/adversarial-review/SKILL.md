---
name: adversarial-review
description: Use after any backtest or research result, before reporting it. A hostile checklist for lookahead, leakage, data snooping, multiple testing, cost and fill errors, and unreproducible results. Ends with a verdict.
---

# Adversarial review

Assume the result is wrong. Try to prove it. Work through this list and write one line per item in the report.

1. **Lookahead:** does any decision use the bar it trades in? Shift the signal one extra bar; a real effect weakens gradually, a leak collapses or flips. Check expiry lists, VIX values and calendar data for future information.
2. **Leakage:** is any holdout or later data present in dev files? Do date filters use `<=` correctly? Is the same day in both train and test?
3. **Data snooping / trials:** how many versions, parameters and windows were tried, including by earlier sessions? Is the p-value corrected? (`ledger.jsonl`)
4. **Controls:** did it beat random entries and a placebo? By how much, with what confidence interval, on how many independent days (not trades)?
5. **Costs:** are tax rates current and applied to the right side? Brokerage per order (two orders per round trip)? Does it survive a higher slippage?
6. **Fills:** could a real order have filled at that price? Limit orders at a target assume the bar traded through it; stops assume no gap. Is liquidity in that strike/time real (volume, OI)?
7. **Survivorship / selection:** skipped signals, missing strikes, dropped outliers, restricted date ranges. Compare traded vs skipped signal days.
8. **Regime and period:** concentrated in a few days or one month? Do results flip by half-year? Rule changes (lot size, expiry weekday, STT) inside the window?
9. **Arithmetic:** reproduce the headline number independently (separate script or by hand on a sample of trades). Recompute gross, costs, net.
10. **Plausibility:** is the Sharpe, win rate or profit factor too good for the mechanism? Real edges on liquid indices are small.

## Verdict (choose one, and say why in two sentences)
`REJECT` (a flaw explains the result) | `INCONCLUSIVE` (cannot tell; say exactly what data/test would decide) | `SURVIVES REVIEW` (still standing; next gate step: ...).
Never write "promising" without a gate step attached.
