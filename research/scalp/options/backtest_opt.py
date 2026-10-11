"""Model-based option-scalp backtest + random-entry control (same idea as the futures harness)."""

from __future__ import annotations

import numpy as np
import pandas as pd

import backtest as fbt  # futures harness: RandomEntry, summarize
from opt_engine import OptionSession


def run(df, vix_by_day: dict, cfg, make_strategy, params, costs, risk, default_iv=0.14):
    trades, daily = [], {}
    for day, g in df.groupby(df["date"].dt.date, sort=True):
        iv = vix_by_day.get(day, default_iv * 100) / 100.0
        s = OptionSession(make_strategy(), params, cfg, costs, iv, risk)
        ts, o, h, l, c = g["date"].tolist(), *(g[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        for k in range(len(g)):
            s.on_bar(ts[k], o[k], h[k], l[k], c[k])
        s.finish(ts[-1])
        trades += s.trades
        daily[day] = s.pnl_rs
    return pd.DataFrame(trades), pd.Series(daily, dtype=float)


def summarize(trades, daily, costs, qty):
    class _Shim:  # reuse the futures summary; its breakeven hook wants a callable
        breakeven_pts = staticmethod(lambda px: costs.breakeven_pts(150.0, qty))
    out = fbt.summarize(trades, daily, _Shim, 0.0)
    if out.get("n_trades"):
        out["avg_gross_pts_per_trade"] = float(trades["gross_pts"].mean())  # premium points
    return out


def null_pvalue(df, vix, cfg, params, costs, risk, observed, n_trades, n_runs=50, seed=0):
    rng = np.random.default_rng(seed)
    bars = max(len(df) - params.warmup * df["date"].dt.date.nunique(), 1)
    p = min(1.0, n_trades / bars * 1.5)
    ex = []
    for _ in range(n_runs):
        t, _d = run(df, vix, cfg, lambda: fbt.RandomEntry(p, rng), params, costs, risk)
        if len(t):
            ex.append(t["net_rs"].mean())
    ex = np.array(ex)
    return float((1 + (ex >= observed).sum()) / (1 + len(ex))), float(ex.mean()) if len(ex) else float("nan")
