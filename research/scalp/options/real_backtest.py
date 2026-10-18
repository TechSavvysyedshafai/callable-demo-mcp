"""Backtest option-buying scalps on REAL expired-option candles (run download_expired_options.py first).

  python real_backtest.py --runs 200
Uses only DEV sessions (the hidden holdout months are never read here). Same random-entry control and trial penalty
as the model-based test. Reports how many signals could not be traded because no saved contract / no option candle."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
for p in (HERE, HERE.parent, HERE.parent.parent):
    sys.path.insert(0, str(p))
import numpy as np
import pandas as pd

import backtest as fbt
import strategy
from contracts import UNDERLYINGS
from costs_opt import OptionCostModel
from engine import Risk
from opt_engine import OptParams
from option_book import OptionBook
from real_engine import RealOptionSession

LEDGER = HERE / "ledger.jsonl"
ALPHA, MIN_TRADES = 0.05, 200


def run(df, book, cfg, make_strategy, params, costs, risk):
    trades, daily, skipped = [], {}, {"no_contract": 0, "no_entry_bar": 0}
    for day, g in df.groupby(df["date"].dt.date, sort=True):
        s = RealOptionSession(make_strategy(), params, cfg, costs, book, risk)
        ts, o, h, l, c = g["date"].tolist(), *(g[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        for k in range(len(g)):
            s.on_bar(ts[k], o[k], h[k], l[k], c[k])
        s.finish(ts[-1])
        trades += s.trades
        daily[day] = s.pnl_rs
        for k, v in s.skipped.items():
            skipped[k] += v
    return pd.DataFrame(trades), pd.Series(daily, dtype=float), skipped


def evaluate(df, book, cfg, trials, runs=50, costs=None):
    costs, risk = costs or OptionCostModel(), Risk()
    params = OptParams(**strategy.OPTIONS)
    trades, daily, skipped = run(df, book, cfg, strategy.make, params, costs, risk)
    import backtest_opt as bo
    res = bo.summarize(trades, daily, costs, cfg["lot"])
    res["skipped_signals"] = skipped
    if res["n_trades"] == 0:
        return {**res, "verdict": "FAIL", "reason": "no trades (check that option files exist for these dates)"}
    rng = np.random.default_rng(0)
    bars = max(len(df) - params.warmup * df["date"].dt.date.nunique(), 1)
    p_entry = min(1.0, (res["n_trades"] + sum(skipped.values())) / bars * 1.5)
    ex = []
    for _ in range(runs):
        t, _d, _s = run(df, book, cfg, lambda: fbt.RandomEntry(p_entry, rng), params, costs, risk)
        if len(t):
            ex.append(t["net_rs"].mean())
    ex = np.array(ex)
    pval = float((1 + (ex >= res["avg_net_rs_per_trade"]).sum()) / (1 + len(ex)))
    alpha_adj = ALPHA / trials
    ok = res["n_trades"] >= MIN_TRADES and res["net_rs"] > 0 and pval <= max(alpha_adj, 1 / (runs + 1))
    return {**res, "null_avg_net_rs_per_trade": float(ex.mean()) if len(ex) else None, "p_vs_random_entries": pval,
            "n_trials": trials, "alpha_adj": alpha_adj, "verdict": "PASS" if ok else "FAIL",
            "note": "REAL option candles; spread is an assumed slippage_rs (candles have no bid/ask)"}


if __name__ == "__main__":
    import kite_data as kd
    a = argparse.ArgumentParser()
    a.add_argument("--underlying", default="NIFTY", choices=["NIFTY"])
    a.add_argument("--interval", default="5minute")
    a.add_argument("--runs", type=int, default=50)
    a.add_argument("--slippage", type=float, default=0.10, help="assumed half-spread per fill in premium rupees")
    a = a.parse_args()
    cfg = dict(UNDERLYINGS[a.underlying])
    book = OptionBook(kd.DEV_DIR / "expired_options" / a.underlying)
    cal = sorted(pd.to_datetime(pd.read_csv(kd.DEV_DIR / "nifty_expiries.csv")["expiry"]).dt.date)
    cfg["calendar"] = cal
    have = sorted({k[0] for k in book.t})
    df = kd.load_dev(a.interval)
    d0 = have[0] - pd.Timedelta(days=9).to_pytimedelta() if have else cal[0]
    df = df[(df["date"].dt.date >= d0) & (df["date"].dt.date <= have[-1])].reset_index(drop=True) if have else df.iloc[:0]
    print(f"{len(book)} option files, expiries {have[0] if have else '-'}..{have[-1] if have else '-'}; {df['date'].dt.date.nunique()} dev sessions")
    h = hashlib.sha256(Path(strategy.__file__).read_bytes() + b"real").hexdigest()[:12]
    seen = {json.loads(l)["hash"] for l in LEDGER.read_text().splitlines() if l} if LEDGER.exists() else set()
    t0 = time.time()
    res = evaluate(df, book, cfg, len(seen | {h}), a.runs, OptionCostModel(slippage_rs=a.slippage))
    with LEDGER.open("a") as fh:
        fh.write(json.dumps({"t": time.time(), "hash": h, "underlying": a.underlying + "-real", "verdict": res["verdict"]}) + "\n")
    print(json.dumps({**res, "seconds": round(time.time() - t0, 1)}, indent=2, default=str))
