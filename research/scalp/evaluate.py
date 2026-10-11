"""Backtest strategy.py on the DEV data with costs, compare against random entries, log the trial.

  python evaluate.py                      # real dev data (python ../fetch_data.py --interval 5minute first)
  python evaluate.py --synthetic-phi 0.3  # dry run on fake data with a planted momentum edge
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import time as dtime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import backtest as bt
import strategy
from costs import CostModel
from engine import EngineParams, Risk
from synth import synthetic_intraday

HERE = Path(__file__).parent
LEDGER = HERE / "ledger.jsonl"
ALPHA, MIN_TRADES = 0.05, 200


def trial_count(h: str) -> int:
    seen = {json.loads(l)["hash"] for l in LEDGER.read_text().splitlines() if l} if LEDGER.exists() else set()
    return len(seen | {h})


def evaluate(df, trials, runs=50, costs=None):
    costs, risk = costs or CostModel(), Risk()
    params = EngineParams(**strategy.ENGINE)
    trades, daily = bt.run(df, strategy.make, params, costs, risk)
    res = bt.summarize(trades, daily, costs, float(df["close"].iloc[-1]))
    if res["n_trades"] == 0:
        return {**res, "verdict": "FAIL", "reason": "no trades"}
    p, null_mean = bt.null_pvalue(df, params, costs, risk, res["avg_net_rs_per_trade"], res["n_trades"], runs)
    alpha_adj = ALPHA / trials
    ok = res["n_trades"] >= MIN_TRADES and res["net_rs"] > 0 and p <= max(alpha_adj, 1 / (runs + 1))
    return {**res, "null_avg_net_rs_per_trade": null_mean, "p_vs_random_entries": p, "n_trials": trials,
            "alpha_adj": alpha_adj, "min_p_possible": 1 / (runs + 1),
            "verdict": "PASS" if ok else "FAIL"}


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--interval", default="5minute")
    a.add_argument("--max-days", type=int, default=500, help="use only the most recent N sessions (speed)")
    a.add_argument("--runs", type=int, default=50, help="random-entry runs for the null; use >=200 for real decisions")
    a.add_argument("--synthetic-phi", type=float, default=None)
    a = a.parse_args()
    if a.synthetic_phi is not None:
        df = synthetic_intraday(n_days=a.max_days, phi=a.synthetic_phi)
    else:
        import kite_data as kd
        df = kd.load_dev(a.interval)
        days = sorted(df["date"].dt.date.unique())[-a.max_days :]
        df = df[df["date"].dt.date.isin(set(days))].reset_index(drop=True)
    h = hashlib.sha256(Path(strategy.__file__).read_bytes()).hexdigest()[:12]
    t0 = time.time()
    res = evaluate(df, trial_count(h), a.runs)
    if a.synthetic_phi is None:  # dry runs do not count as trials
        with LEDGER.open("a") as fh:
            fh.write(json.dumps({"t": time.time(), "hash": h, "verdict": res["verdict"]}) + "\n")
    print(json.dumps({**res, "seconds": round(time.time() - t0, 1)}, indent=2, default=str))
