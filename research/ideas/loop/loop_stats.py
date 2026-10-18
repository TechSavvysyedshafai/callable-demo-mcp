"""Statistics for the loop. Reuses the Task 5 helpers (bootstrap_p, null_p, halves, Trades) without editing them.
Only two things are re-stated here, because the Task 5 versions have the batch-1 numbers (cost 0.10%, alpha 0.005) built in:
the verdict (alpha is a parameter) and the evaluation (cost is a parameter). Tests prove they equal Task 5 at its own settings."""

from __future__ import annotations

import numpy as np

import loop_config as cfg
import rule_engine  # noqa: F401  (puts research/ideas on sys.path)
import forced_trader_ideas as fi


def verdict_with_alpha(r: dict, alpha: float) -> tuple:
    """Same pass rule as fi.verdict: (a) net mean > 0, (b) bootstrap p < alpha, (c) random-entry p < alpha, (d) both halves positive, (e) >= 60 trades."""
    a = bool(r["n_trades"] > 0 and r["mean_net"] > 0)
    b = bool(r["boot_p"] < alpha)
    c = bool(r["null_p"] < alpha)
    d = bool(r["first_n"] > 0 and r["second_n"] > 0 and r["first_mean"] > 0 and r["second_mean"] > 0)
    e = bool(r["n_trades"] >= cfg.MIN_DEV_TRADES)
    checks = {"a_mean_net_positive": a, "b_boot_p": b, "c_null_p": c, "d_both_halves_positive": d, "e_min_60_trades": e}
    if a and b and c and d and e:
        return "SURVIVES", checks
    if a and b:
        return "INCONCLUSIVE", checks
    return "REJECT", checks


def max_drawdown(returns) -> float:
    """Largest peak-to-trough fall of the running SUM of per-trade net returns (start counts as a peak of 0). Zero if it never falls."""
    x = np.asarray(returns, float)
    if len(x) == 0:
        return 0.0
    cum = np.concatenate([[0.0], np.cumsum(x)])
    return float(np.max(np.maximum.accumulate(cum) - cum))


def evaluate(t: "fi.Trades", cost: float, alpha: float) -> dict:
    """Mirror of fi.evaluate_idea with the batch cost and the batch alpha."""
    net, gross_dir = t.net(cost), t.net(0.0)
    n = len(net)
    res = {"idea": t.idea, "name": t.name, "n_trades": n, "window": [str(t.window[0]), str(t.window[1])],
           "win_rate": float((net > 0).mean()) if n else float("nan"),
           "mean_net": float(net.mean()) if n else float("nan"), "mean_gross": float(gross_dir.mean()) if n else float("nan"),
           "boot_p": fi.bootstrap_p(net), "boot_p_zero_cost": fi.bootstrap_p(gross_dir)}
    res["null_p"], res["null_mean"], res["null_q95"] = fi.null_p(t, cost)
    res["null_p_zero_cost"] = fi.null_p(t, 0.0)[0]
    res.update(fi.halves(t, cost))
    res["dev_max_drawdown"] = max_drawdown(net)
    res["alpha"], res["cost"] = alpha, cost
    res["verdict"], res["checks"] = verdict_with_alpha(res, alpha)
    return res
