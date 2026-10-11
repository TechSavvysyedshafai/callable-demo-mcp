"""Model-based backtest of option-buying scalps driven by scalp/strategy.py's signal.

  python evaluate_opt.py --underlying NIFTY --synthetic-phi 0.5     # self-check on fake data
  python evaluate_opt.py --underlying NIFTY                         # real dev index bars + India VIX
(premiums are Black-Scholes with constant intraday IV: indicative, NOT proof. Real proof = recorded quotes.)
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
for p in (HERE, HERE.parent, HERE.parent.parent):
    sys.path.insert(0, str(p))
import backtest_opt as bo
import strategy
from contracts import UNDERLYINGS
from costs_opt import OptionCostModel
from engine import Risk
from opt_engine import OptParams
from synth import synthetic_intraday

LEDGER = HERE / "ledger.jsonl"
ALPHA, MIN_TRADES = 0.05, 200


def evaluate(df, vix, cfg, trials, runs=50, costs=None):
    costs, risk = costs or OptionCostModel(), Risk()
    params = OptParams(**strategy.OPTIONS)
    trades, daily = bo.run(df, vix, cfg, strategy.make, params, costs, risk)
    res = bo.summarize(trades, daily, costs, cfg["lot"])
    import numpy as np
    r = np.log(df["close"] / df["open"])
    bars_per_day = len(df) / df["date"].dt.date.nunique()
    res["realized_vol_pct"] = float(r.std() * np.sqrt(bars_per_day * 250) * 100)
    res["mean_iv_pct"] = float(np.mean(list(vix.values())))
    res["breakeven_underlying_pts_at_delta_0.5"] = float(2 * costs.breakeven_pts(150.0, cfg["lot"]))
    if res["n_trades"] == 0:
        return {**res, "verdict": "FAIL", "reason": "no trades"}
    p, null_mean = bo.null_pvalue(df, vix, cfg, params, costs, risk, res["avg_net_rs_per_trade"], res["n_trades"], runs)
    alpha_adj = ALPHA / trials
    ok = (res["n_trades"] >= MIN_TRADES and res["net_rs"] > 0 and p <= max(alpha_adj, 1 / (runs + 1))
          and res["realized_vol_pct"] < res["mean_iv_pct"])
    return {**res, "null_avg_net_rs_per_trade": null_mean, "p_vs_random_entries": p, "n_trials": trials,
            "alpha_adj": alpha_adj, "verdict": "PASS" if ok else "FAIL",
            "warning": "model-based premiums (Black-Scholes, constant intraday IV): indicative only"
            + ("; INVALID: realized vol >= implied vol flatters option buyers" if res["realized_vol_pct"] >= res["mean_iv_pct"] else "")}


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--underlying", default="NIFTY", choices=list(UNDERLYINGS))
    a.add_argument("--interval", default="5minute")
    a.add_argument("--max-days", type=int, default=300)
    a.add_argument("--runs", type=int, default=50)
    a.add_argument("--synthetic-phi", type=float, default=None)
    a = a.parse_args()
    cfg = UNDERLYINGS[a.underlying]
    if a.synthetic_phi is not None:
        df = synthetic_intraday(n_days=a.max_days, phi=a.synthetic_phi, bar_vol=0.0008)
        vix = {d: 14.0 for d in df["date"].dt.date.unique()}
    else:
        import pandas as pd
        import kite_data as kd
        df = kd.load_dev(a.interval)  # index bars; for non-NIFTY run fetch_data.py with that underlying's token
        days = sorted(df["date"].dt.date.unique())[-a.max_days:]
        df = df[df["date"].dt.date.isin(set(days))].reset_index(drop=True)
        v = pd.read_csv(kd.DEV_DIR / "india_vix_day.csv", parse_dates=["date"])
        vix = dict(zip(v["date"].dt.date, v["close"]))
    h = hashlib.sha256((Path(strategy.__file__).read_bytes() + a.underlying.encode())).hexdigest()[:12]
    seen = {json.loads(l)["hash"] for l in LEDGER.read_text().splitlines() if l} if LEDGER.exists() else set()
    t0 = time.time()
    res = evaluate(df, vix, cfg, len(seen | {h}), a.runs)
    if a.synthetic_phi is None:
        with LEDGER.open("a") as fh:
            fh.write(json.dumps({"t": time.time(), "hash": h, "underlying": a.underlying, "verdict": res["verdict"]}) + "\n")
    print(json.dumps({**res, "seconds": round(time.time() - t0, 1)}, indent=2, default=str))
