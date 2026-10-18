"""Evaluate SELL1 (weekly iron condor V1/V2) at slippage Rs0.10/0.20/0.30 and apply the PRE-REGISTERED pass rule.

  python evaluate.py            # writes results/selling_results.json and results/selling_results.md
The pass rule (fixed before any data): at slippage 0.20, (a) mean weekly net > 0 and the 90% block-bootstrap interval
(4-week blocks, 5,000 resamples) has lower bound > 0, (b) total net >= 2 x worst single-week loss, (c) mean still > 0 at 0.30.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import backtest as bt  # noqa: E402

SLIPS = (0.10, 0.20, 0.30)
BLOCK, N_BOOT, SEED = 4, 5000, 20261018
CAPITAL_PER_LOT = 2 * bt.WING * bt.LOT  # ASSUMPTION: 2 x maximum structure loss (width bound), Rs22,500; real margin unknown
CASH_RATE = 0.065  # what doing nothing could earn on that capital (repo's cash assumption)


def block_bootstrap_ci(x, block=BLOCK, n=N_BOOT, seed=SEED, level=0.90):
    """Overlapping moving-block bootstrap of the mean: (lo, hi) = (5th, 95th) percentile of resampled means."""
    x = np.asarray(x, float)
    m = len(x)
    rng = np.random.default_rng(seed)
    k = int(np.ceil(m / block))
    starts = rng.integers(0, m - block + 1, size=(n, k))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)[:, :m]
    means = x[idx].mean(axis=1)
    a = (1 - level) / 2
    return float(np.quantile(means, a)), float(np.quantile(means, 1 - a))


max_drawdown = bt.max_drawdown


def longest_losing_streak(x):
    best = cur = 0
    for v in x:
        cur = cur + 1 if v < 0 else 0
        best = max(best, cur)
    return best


def summarize(weeks):
    traded = [w for w in weeks if w.skipped is None]
    skipped = [w for w in weeks if w.skipped is not None]
    x = np.array([w.net_rs for w in traded], float)
    out = {"weeks_total": len(weeks), "weeks_traded": len(traded), "weeks_skipped": len(skipped),
           "skip_reasons": {r: sum(1 for w in skipped if w.skipped == r) for r in sorted({w.skipped for w in skipped})}}
    if len(x) == 0:
        return out
    lo, hi = block_bootstrap_ci(x) if len(x) > BLOCK else (float("nan"), float("nan"))
    worst = float(x.min())
    out.update(
        win_rate=float((x > 0).mean()), mean_net=float(x.mean()), median_net=float(np.median(x)), total_net=float(x.sum()),
        worst_week=worst, best_week=float(x.max()), max_drawdown=max_drawdown(x), longest_losing_streak=longest_losing_streak(x),
        breach_rate=float(np.mean([w.breach for w in traded])), stopped_rate=float(np.mean([w.stopped for w in traded])),
        ci90_lo=lo, ci90_hi=hi, mean_credit_pts=float(np.mean([w.credit for w in traded])),
        mean_costs_rs=float(np.mean([w.costs_rs for w in traded])), mean_gross_rs=float(np.mean([w.gross_pts * bt.LOT for w in traded])),
        ret_on_capital_total=float(x.sum() / CAPITAL_PER_LOT), cash_alternative_total=float(CAPITAL_PER_LOT * CASH_RATE * len(x) / 52),
    )
    return out


def pass_rule(results_by_slip):
    r2, r3 = results_by_slip.get("0.2"), results_by_slip.get("0.3")
    if not r2 or "mean_net" not in r2 or not r3 or "mean_net" not in r3:
        return {"useful": False, "reason": "no data"}
    a = r2["mean_net"] > 0 and r2["ci90_lo"] > 0
    b = r2["total_net"] >= 2 * abs(min(r2["worst_week"], 0.0)) and r2["total_net"] > 0
    c = r3["mean_net"] > 0
    return {"a_mean_pos_and_ci_lo_pos": bool(a), "b_total_ge_2x_worst": bool(b), "c_mean_pos_at_0.30": bool(c), "useful": bool(a and b and c)}


def main():
    res = {}
    for v in ("V1", "V2"):
        res[v] = {"by_slip": {}}
        for s in SLIPS:
            weeks = bt.run_all(v, s)
            res[v]["by_slip"][str(s)] = summarize(weeks)
            if s == 0.20:
                res[v]["weeks_0.20"] = [
                    {"expiry": w.expiry.isoformat(), "skipped": w.skipped, "entry": str(w.entry_ts), "spot": w.spot,
                     "strikes": {k: v_[0] for k, v_ in w.strikes.items()}, "credit": w.credit, "settle": w.settle,
                     "stopped": w.stopped, "stop_ts": str(w.stop_ts), "gross_pts": w.gross_pts, "costs_rs": w.costs_rs,
                     "net_rs": w.net_rs, "breach": w.breach} for w in weeks]
        res[v]["pass_rule"] = pass_rule(res[v]["by_slip"])
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "selling_results.json").write_text(json.dumps(res, indent=1, default=str))
    rows = ["| Variant | Slip | Traded | Skipped | Win% | Mean Rs | Median Rs | Total Rs | Worst wk Rs | Max DD Rs | Loss streak | Breach% | Stopped% | 90% CI of mean |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in res:
        for s, r in res[v]["by_slip"].items():
            if "mean_net" not in r:
                continue
            rows.append(f"| {v} | {s} | {r['weeks_traded']} | {r['weeks_skipped']} | {100*r['win_rate']:.0f} | {r['mean_net']:,.0f} | {r['median_net']:,.0f} | "
                        f"{r['total_net']:,.0f} | {r['worst_week']:,.0f} | {r['max_drawdown']:,.0f} | {r['longest_losing_streak']} | {100*r['breach_rate']:.0f} | "
                        f"{100*r['stopped_rate']:.0f} | {r['ci90_lo']:,.0f} to {r['ci90_hi']:,.0f} |")
    (out / "selling_results.md").write_text("\n".join(rows) + "\n\n" + json.dumps({v: res[v]["pass_rule"] for v in res}, indent=1) + "\n")
    print("\n".join(rows))
    for v in res:
        print(v, res[v]["pass_rule"])


if __name__ == "__main__":
    main()
