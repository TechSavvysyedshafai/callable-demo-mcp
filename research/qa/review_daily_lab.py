"""Adversarial review of the daily range-forecast PASS (pre-registered in research/RESULTS.md, section P4).

  python research/qa/review_daily_lab.py
Imports the frozen harness only for (a) the lookahead tests and (b) the comparison number; every other statistic uses the independent
forecasts from repro_daily_mae.py. It never calls harness.log_trial, so the trial ledger is untouched. Dev data only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(HERE))
import repro_daily_mae as rp  # noqa: E402

PERM_DRAWS, PERM_SEED = 2000, 12345


def gain(y, cand, base):
    """Relative MAE gain of the candidate over the baseline (positive = candidate better)."""
    b = np.mean(np.abs(y - base))
    return float((b - np.mean(np.abs(y - cand))) / b)


def lookahead_tests() -> dict:
    import harness as h
    import kite_data as kd
    from candidate import predict

    df = kd.load_dev("day")
    full = {"candidate": h.walk_forward(df, predict)}
    full.update({k: h.walk_forward(df, fn) for k, fn in h.BASELINES.items()})
    out = {}
    rng = np.random.default_rng(7)
    for N in (1000, 1500):
        trunc = df.iloc[:N].reset_index(drop=True)
        junk = df.copy()
        n_junk = len(junk) - N
        px = 1000 + rng.random(n_junk) * 50000  # wild prices, bigger and smaller than anything real
        junk.loc[N:, "low"] = px
        junk.loc[N:, "high"] = px * (1 + rng.random(n_junk))
        junk.loc[N:, "open"] = px
        junk.loc[N:, "close"] = px
        for name, fn in {"candidate": predict, **h.BASELINES}.items():
            a = h.walk_forward(trunc, fn)
            b = h.walk_forward(junk, fn)
            k = len(a)  # origins 250..N-2
            ref = full[name].iloc[:k]
            d_trunc = float(np.max(np.abs(a["mean"].to_numpy() - ref["mean"].to_numpy())))
            d_junk = float(np.max(np.abs(b["mean"].iloc[:k].to_numpy() - ref["mean"].to_numpy())))
            d_y = float(np.max(np.abs(a["y"].to_numpy() - ref["y"].to_numpy())))
            out[f"N={N} {name}"] = {"origins_compared": k, "max_abs_diff_truncated": d_trunc, "max_abs_diff_future_garbage": d_junk, "max_abs_diff_target": d_y}
    out["lookahead_found"] = any(v["max_abs_diff_truncated"] > 1e-12 or v["max_abs_diff_future_garbage"] > 1e-12 or v["max_abs_diff_target"] > 1e-12
                                 for v in out.values() if isinstance(v, dict))
    return out


def harness_numbers() -> dict:
    import harness as h
    import kite_data as kd
    from candidate import predict

    res = h.evaluate(kd.load_dev("day"), predict, trials=1)  # same call evaluate.py makes; log_trial deliberately NOT called
    return {k: res[k] for k in ("n_origins", "mae", "pinball", "best_baseline", "rel_improvement", "ci_lower_gain", "verdict")}


def main() -> dict:
    dates, r = rp.load()
    f = rp.forecasts(r)
    y, cand, ew = f["y"], f["candidate"], f["ewma94"]
    tdates = pd.to_datetime(dates[f["origins"] + 1])
    n = len(y)
    obs = gain(y, cand, ew)
    res = {"n_origins": n, "observed_rel_gain_vs_ewma94": obs}

    # (c) placebos: forecasts fixed, realised targets destroyed
    rng = np.random.default_rng(PERM_SEED)
    perm = np.array([gain(y[rng.permutation(n)], cand, ew) for _ in range(PERM_DRAWS)])
    shifts = np.arange(30, n - 30)
    circ = np.array([gain(np.roll(y, int(s)), cand, ew) for s in shifts])
    for name, arr in (("shuffle", perm), ("circular_shift", circ)):
        p95 = float(np.quantile(arr, 0.95))
        res[f"placebo_{name}"] = {
            "draws": len(arr), "mean_gain": float(arr.mean()), "median_gain": float(np.median(arr)), "p95_gain": p95,
            "max_gain": float(arr.max()), "perm_p_value": float((1 + (arr >= obs).sum()) / (1 + len(arr))),
            "similar_gain": bool(obs <= p95 or np.median(arr) >= 0.5 * obs),
        }

    # (d) three consecutive chunks
    d = np.abs(y - ew) - np.abs(y - cand)
    total = d.sum()
    chunks = []
    for k, idx in enumerate(np.array_split(np.arange(n), 3), 1):
        chunks.append({"chunk": k, "from": str(tdates[idx[0]].date()), "to": str(tdates[idx[-1]].date()), "n": len(idx),
                       "mae_candidate": float(np.mean(np.abs(y[idx] - cand[idx]))), "mae_ewma94": float(np.mean(np.abs(y[idx] - ew[idx]))),
                       "rel_gain": gain(y[idx], cand[idx], ew[idx]), "share_of_total_gain": float(d[idx].sum() / total)})
    res["chunks"] = chunks
    res["max_chunk_share"] = max(c["share_of_total_gain"] for c in chunks)
    res["chunks_where_candidate_wins"] = sum(c["rel_gain"] > 0 for c in chunks)

    # informational (do not change the verdict)
    yr = pd.Series(d, index=tdates).groupby(tdates.year).agg(["sum", "size"])
    res["info_gain_by_year"] = {int(k): {"n": int(v["size"]), "share_of_total_gain": float(v["sum"] / total)} for k, v in yr.iterrows()}
    covid = (tdates >= "2020-03-01") & (tdates <= "2020-06-30")
    res["info_without_covid_window_2020_03_to_06"] = {"n": int((~covid).sum()), "rel_gain": gain(y[~covid], cand[~covid], ew[~covid]),
                                                      "share_of_total_gain_inside_window": float(d[covid].sum() / total)}
    daily_range = pd.Series(r, index=pd.to_datetime(dates))
    special = daily_range.index.dayofweek >= 5  # weekend sessions; plus very short weekday sessions (range below 0.3%, mostly Muhurat)
    special |= (daily_range < 0.003).to_numpy()
    sp_dates = set(daily_range.index[special])
    flag_t = np.array([t in sp_dates for t in tdates])
    flag_o = np.array([pd.Timestamp(str(dates[i])) in sp_dates for i in f["origins"]])
    keep = ~(flag_t | flag_o)
    res["info_special_sessions"] = {"flagged_days_in_file": int(special.sum()), "origins_dropped": int((~keep).sum()),
                                    "rel_gain_without": gain(y[keep], cand[keep], ew[keep]),
                                    "flagged_dates": sorted(str(x.date()) for x in daily_range.index[special])}
    res["info_bias"] = {"mean_y": float(y.mean()), "mean_candidate": float(cand.mean()), "mean_ewma94": float(ew.mean())}
    return res


if __name__ == "__main__":
    out = {"independent_repro": rp.summarize(), "harness": harness_numbers(), "lookahead": lookahead_tests(), "review": main()}
    print(json.dumps(out, indent=2, default=str))
