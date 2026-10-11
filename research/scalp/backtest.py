"""Run a strategy over many sessions; compare with random entries under identical exits and costs."""

from __future__ import annotations

import numpy as np
import pandas as pd

from engine import EngineParams, Risk, SessionEngine


class RandomEntry:
    """Null model: enters in a random direction with probability p per eligible bar."""

    def __init__(self, p: float, rng: np.random.Generator):
        self.p, self.rng = p, rng

    def on_bar(self, o, h, l, c):
        return 0 if self.rng.random() > self.p else (1 if self.rng.random() < 0.5 else -1)


def run(df: pd.DataFrame, make_strategy, params: EngineParams, costs, risk: Risk):
    trades, daily = [], {}
    for day, g in df.groupby(df["date"].dt.date, sort=True):
        eng = SessionEngine(make_strategy(), params, costs, risk)
        ts, o, h, l, c = g["date"].tolist(), *(g[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        for k in range(len(g)):
            eng.on_bar(ts[k], o[k], h[k], l[k], c[k])
        eng.finish(ts[-1])
        trades += eng.trades
        daily[day] = eng.pnl_rs
    return pd.DataFrame(trades), pd.Series(daily, dtype=float)


def summarize(trades: pd.DataFrame, daily: pd.Series, costs, ref_price: float) -> dict:
    if trades.empty:
        return {"n_trades": 0}
    dd = (daily.cumsum() - daily.cumsum().cummax()).min()
    sd = daily.std()
    return {
        "n_trades": int(len(trades)),
        "n_days": int(len(daily)),
        "win_rate": float((trades["net_rs"] > 0).mean()),
        "net_rs": float(trades["net_rs"].sum()),
        "gross_rs_before_costs": float((trades["net_rs"] + trades["cost_rs"]).sum()),
        "cost_rs": float(trades["cost_rs"].sum()),
        "avg_net_rs_per_trade": float(trades["net_rs"].mean()),
        "breakeven_pts_per_round_trip": float(costs.breakeven_pts(ref_price)),
        "avg_gross_pts_per_trade": float(trades["gross_pts"].mean()),
        "max_drawdown_rs": float(dd),
        "daily_sharpe_annualised": float(daily.mean() / sd * np.sqrt(250)) if sd > 0 else 0.0,
        "exits": trades["why"].value_counts().to_dict(),
    }


def null_pvalue(df, params, costs, risk, observed_expectancy, n_trades, n_runs=50, seed=0):
    """Fraction of random-entry runs whose avg net Rs/trade >= the strategy's. Small = signal beats chance."""
    rng = np.random.default_rng(seed)
    bars = max(len(df) - (params.sigma_window + 1) * df["date"].dt.date.nunique(), 1)
    p = min(1.0, n_trades / bars * 1.5)  # roughly match trade frequency (entries are blocked while in a trade)
    ex = []
    for _ in range(n_runs):
        t, _d = run(df, lambda: RandomEntry(p, rng), params, costs, risk)
        if len(t):
            ex.append(t["net_rs"].mean())
    ex = np.array(ex)
    return float((1 + (ex >= observed_expectancy).sum()) / (1 + len(ex))), float(ex.mean()) if len(ex) else float("nan")
