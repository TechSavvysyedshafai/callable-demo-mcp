"""Hostile review of B6-01 (skill adversarial-review). INFORMATION ONLY: none of this is a trial, none of it changes a rule or a verdict.
  python research/goldsilver/gs_review.py     (needs results/goldsilver_results.json from gs_run.py)"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gs_core as gc  # noqa: E402


def main() -> None:
    df, _ = gc.load()
    base = gc.simulate(df)["trades"]
    net = gc.net_returns(base)
    out = {}
    # 1. lookahead / delay: use the open of the row AFTER the one the rule uses, for entry and exit (one extra bar of delay)
    d1 = df.copy()
    d1["g_open"], d1["s_open"] = df["g_open"].shift(-1), df["s_open"].shift(-1)
    d1 = d1.iloc[:-1].reset_index(drop=True)
    t1 = gc.simulate(d1)["trades"]
    out["delay_1_bar"] = {"n": len(t1), "mean_net": float(gc.net_returns(t1).mean()), "mean_gross": float(gc.net_returns(t1, zero_cost=True).mean())}
    # 2. concentration: biggest losers and the sample without them
    order = np.argsort(net)
    out["worst3"] = [{"entry": base[i]["entry_date"], "exit": base[i]["exit_date"], "dir": base[i]["direction"], "net": float(net[i])} for i in order[:3]]
    out["mean_without_worst"] = float(np.delete(net, order[0]).mean())
    out["mean_without_worst3"] = float(np.delete(net, order[:3]).mean())
    out["median_net"] = float(np.median(net))
    out["sum_of_net_excluding_worst"] = float(np.delete(net, order[0]).sum())
    # 3. placebo: take the OPPOSITE side of every signal (trend-following instead of mean reversion), same dates, same costs
    flip = -np.array([t["gross"] for t in base]) - gc.trade_cost([t["cal_days"] for t in base], [t["hold"] for t in base])
    out["placebo_flipped_signal"] = {"mean_net": float(flip.mean()), "boot_p": gc.fi.bootstrap_p(flip, gc.BLOCK, gc.N_BOOT, gc.SEED)}
    # 4. cost sweep
    gross = np.array([t["gross"] for t in base])
    cal = np.array([t["cal_days"] for t in base], float)
    out["cost_sweep_mean_net"] = {f"x{m}": float((gross - m * (gc.COST_RT + gc.FIN_PER_DAY * cal)).mean()) for m in (0, 0.5, 1, 2)}
    out["breakeven_cost_multiple"] = float(gross.mean() / (gc.COST_RT + gc.FIN_PER_DAY * cal).mean()) if gross.mean() > 0 else None
    out["mean_cost_per_trade"] = float((gc.COST_RT + gc.FIN_PER_DAY * cal).mean())
    # 5. power: what true mean could 26 trades detect at alpha 0.003125 (one-sided normal approx)?
    sd = float(net.std(ddof=1))
    out["power"] = {"sd_per_trade": sd, "n": len(net), "se_of_mean": sd / np.sqrt(len(net)), "detectable_mean_at_alpha_z2.74": 2.74 * sd / np.sqrt(len(net)),
                    "ci95_of_mean": [float(net.mean() - 1.96 * sd / np.sqrt(len(net))), float(net.mean() + 1.96 * sd / np.sqrt(len(net)))]}
    # 6. data sanity around the worst trade and the biggest one-day moves (adjustment / split artefacts would show as a jump in only one leg)
    w = base[order[0]]
    a, b = pd.Timestamp(w["entry_date"]), pd.Timestamp(w["exit_date"])
    seg = df[(df["date"] >= a) & (df["date"] <= b)]
    out["worst_trade_path"] = {"gold_open": [float(seg["g_open"].iloc[0]), float(seg["g_open"].iloc[-1])], "silver_open": [float(seg["s_open"].iloc[0]), float(seg["s_open"].iloc[-1])],
                               "gold_ret": float(seg["g_open"].iloc[-1] / seg["g_open"].iloc[0] - 1), "silver_ret": float(seg["s_open"].iloc[-1] / seg["s_open"].iloc[0] - 1)}
    for nm, c in (("gold", "g_close"), ("silver", "s_close")):
        ret = df[c].pct_change()
        big = ret.abs().nlargest(5).index
        out[f"top5_moves_{nm}"] = [{"date": str(df.loc[i, "date"].date()), "ret": float(ret[i])} for i in big]
    ratio = df["g_close"] / df["s_close"]
    out["ratio_range"] = {"min": float(ratio.min()), "max": float(ratio.max()), "first": float(ratio.iloc[0]), "last": float(ratio.iloc[-1])}
    # 7. regime: trades by calendar year, and gross by direction
    yr = pd.Series(net, index=pd.to_datetime([t["entry_date"] for t in base])).groupby(lambda x: x.year)
    out["by_year"] = {int(k): {"n": int(len(v)), "mean_net": float(v.mean())} for k, v in yr}
    out["by_direction"] = {"long_gold_short_silver": float(net[[t["direction"] > 0 for t in base]].mean()), "short_gold_long_silver": float(net[[t["direction"] < 0 for t in base]].mean())}
    out["time_in_market_share"] = float(sum(t["hold"] for t in base) / (len(df) - gc.LOOKBACK))
    # 8. exit-reason breakdown
    out["by_reason"] = {k: {"n": int(sum(t["reason"] == k for t in base)), "mean_net": float(np.mean([n for t, n in zip(base, net) if t["reason"] == k])) if any(t["reason"] == k for t in base) else None} for k in ("revert", "stop", "time")}
    (HERE / "results" / "goldsilver_review.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
