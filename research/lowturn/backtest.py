"""Daily, vectorised backtest for low-turnover NIFTY exposure rules. No order code; research only.

Timing: a weight w[t] is decided with information up to day t's CLOSE and traded at day t+1's OPEN.
Day t+1 return = w[t-1]*overnight gap + w[t]*(open->close) + (1-w[t])*cash_daily - cost*|w[t]-w[t-1]|.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CASH_RATE = 0.065
DAYS = 252
COSTS = (0.0010, 0.0025, 0.0050)


def cash_daily(rate: float = CASH_RATE) -> float:
    return (1 + rate) ** (1 / DAYS) - 1


# ---- signals: each returns exposure w[t] in [0,1] using data up to the close of day t ----
def signal_buyhold(df: pd.DataFrame) -> pd.Series:
    return pd.Series(1.0, index=df.index)


def signal_sma(df: pd.DataFrame, window: int = 200) -> pd.Series:
    """S1: hold when close > simple moving average of the last `window` closes (including today). NaN until defined."""
    sma = df["close"].rolling(window).mean()
    w = (df["close"] > sma).astype(float)
    return w.where(sma.notna())


def signal_monthly(df: pd.DataFrame, months: int = 10) -> pd.Series:
    """S2: on each month's last trading day, hold next month if close > mean of the last `months` month-end closes
    (including this one). Weight is carried forward between month-ends. NaN until defined."""
    d = df["date"]
    ym = d.dt.year * 100 + d.dt.month
    is_me = ym != ym.shift(-1)  # last trading day of the month in the data (the final bar is a month-end only if the month ended)
    me_close = df["close"].where(is_me)
    avg = me_close.dropna().rolling(months).mean()
    w = pd.Series(np.nan, index=df.index)
    sig = (df["close"].loc[avg.index] > avg).astype(float).where(avg.notna())
    w.loc[sig.index] = sig
    return w.ffill()


def signal_voltarget(df: pd.DataFrame, target: float = 0.12, predict=None) -> pd.Series:
    """S3: exposure = min(1, target / forecast annualised vol). Forecast = candidate.predict (HAR range) -> Parkinson sigma."""
    if predict is None:
        from candidate import predict as predict  # the existing, unmodified research/candidate.py
    hi_lo = df[["high", "low"]]
    w = np.full(len(df), np.nan)
    for t in range(59, len(df)):
        hist = df.iloc[t - 59 : t + 1]  # up to and including today's close; predict reads only the last 60 bars
        m = predict(hist)["mean"]
        sigma_ann = DAYS ** 0.5 * m / (2 * (2 / np.pi) ** 0.5)
        w[t] = min(1.0, target / sigma_ann) if sigma_ann > 0 else 1.0
    return pd.Series(w, index=df.index)


# ---- engine ----
def run(df: pd.DataFrame, w: pd.Series, cost: float = 0.0025, cash_rate: float = CASH_RATE, start: int | None = None) -> pd.DataFrame:
    """Daily results from index `start` (default: first day where w is defined; first traded day is start+1).
    Returns frame with date, ret (net daily return), w_held (weight held at the close), turnover, gross."""
    o, c = df["open"].to_numpy(float), df["close"].to_numpy(float)
    wv = w.to_numpy(float)
    if start is None:
        start = int(np.flatnonzero(~np.isnan(wv))[0])
    n = len(df)
    gap = np.r_[np.nan, o[1:] / c[:-1] - 1]
    intra = c / o - 1
    rf = cash_daily(cash_rate)
    idx = np.arange(start + 1, n)  # day t+1 for decisions t = start .. n-2
    w_new = wv[idx - 1]  # decided at close of previous day, held from this open
    w_old = np.r_[0.0, wv[idx[:-1] - 1]]  # weight held overnight into this open (0 = flat before the first trade)
    turn = np.abs(w_new - w_old)
    gross = w_old * gap[idx] + w_new * intra[idx] + (1 - w_new) * rf
    ret = gross - cost * turn
    return pd.DataFrame({"date": df["date"].to_numpy()[idx], "ret": ret, "gross": gross, "w": w_new, "turnover": turn})


# ---- metrics ----
def max_drawdown(ret: np.ndarray) -> float:
    wealth = np.cumprod(1 + ret)
    peak = np.maximum.accumulate(np.r_[1.0, wealth])[1:]
    return float((wealth / peak - 1).min())


def years_between(dates: pd.Series) -> float:
    return (dates.iloc[-1] - dates.iloc[0]).days / 365.25


def metrics(res: pd.DataFrame, cash_rate: float = CASH_RATE) -> dict:
    r = res["ret"].to_numpy()
    yrs = years_between(res["date"])
    cagr = float(np.prod(1 + r) ** (1 / yrs) - 1)
    vol = float(r.std(ddof=1) * DAYS ** 0.5)
    mdd = max_drawdown(r)
    ex = r - cash_daily(cash_rate)
    sharpe = float(ex.mean() / r.std(ddof=1) * DAYS ** 0.5) if r.std() > 0 else float("nan")
    yearly = (1 + res.set_index("date")["ret"]).groupby(res["date"].dt.year.to_numpy()).prod() - 1
    counts = res.groupby(res["date"].dt.year.to_numpy()).size()
    full = yearly[counts >= 200]  # ignore partial calendar years for "worst year"
    if full.empty:  # short slices (e.g. unit tests): fall back to every year present
        full = yearly
    return {
        "cagr": cagr, "vol": vol, "max_dd": mdd, "sharpe": sharpe,
        "calmar": float(cagr / abs(mdd)) if mdd < 0 else float("nan"),
        "pct_invested": float(res["w"].mean()), "switches_per_year": float(res["turnover"].sum() / yrs),
        "worst_year": float(full.min()), "worst_year_which": int(full.idxmin()), "years": yrs, "days": len(r),
    }


def halves(res: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = len(res) // 2
    return res.iloc[:m].reset_index(drop=True), res.iloc[m:].reset_index(drop=True)


def calendar_years(res: pd.DataFrame) -> pd.Series:
    return (1 + res.set_index("date")["ret"]).groupby(res["date"].dt.year.to_numpy()).prod() - 1


# ---- bootstrap ----
def block_bootstrap(strat: np.ndarray, bench: np.ndarray, years: float, block: int = 63, n: int = 2000, seed: int = 0) -> dict:
    """Circular moving-block bootstrap on paired daily returns. 90% interval = 5th..95th percentile."""
    rng = np.random.default_rng(seed)
    T = len(strat)
    nb = -(-T // block)
    d_cagr, dd_ratio = np.empty(n), np.empty(n)
    for i in range(n):
        starts = rng.integers(0, T, nb)
        ix = ((starts[:, None] + np.arange(block)[None, :]) % T).ravel()[:T]
        s, b = strat[ix], bench[ix]
        d_cagr[i] = np.prod(1 + s) ** (1 / years) - np.prod(1 + b) ** (1 / years)
        dd_ratio[i] = max_drawdown(s) / max_drawdown(b)
    q = lambda a: [float(np.percentile(a, 5)), float(np.percentile(a, 95))]
    return {"cagr_diff_90ci": q(d_cagr), "dd_ratio_90ci": q(dd_ratio), "block": block, "n": n}


# ---- after-tax (current Indian rates applied to all history; counterfactual) ----
STCG, LTCG, HOLD_DAYS = 0.20, 0.125, 365


def _fy(ts) -> int:
    ts = pd.Timestamp(ts)
    return ts.year if ts.month >= 4 else ts.year - 1


def after_tax(res: pd.DataFrame, exemption: float = 0.0, capital: float = 1_000_000.0) -> dict:
    """All-in / all-out rules only (w in {0,1}). One episode = entry trade .. exit trade. Tax is paid at each exit on the
    equity-phase gain (costs count as part of the basis); losses carry forward and offset later gains of either kind
    (a simplification of the real ST/LT loss rules). If still invested at the end, it is treated as sold on the last day.
    Cash-leg interest is NOT taxed (favours the strategies). `exemption` = Rs per financial year on long-term gains."""
    r, w, dates = res["ret"].to_numpy(), res["w"].to_numpy(), pd.to_datetime(res["date"]).to_numpy()
    wealth, pool, basis, entry_d = capital, 0.0, None, None
    fy_used: dict[int, float] = {}
    tax_st = tax_lt = gain_st = gain_lt = 0.0
    hold, n_ep = [], 0

    def settle(i):
        nonlocal wealth, pool, tax_st, tax_lt, gain_st, gain_lt, n_ep
        gain = wealth - basis
        days = (dates[i] - entry_d) / np.timedelta64(1, "D")
        lt = days > HOLD_DAYS
        hold.append(days)
        n_ep += 1
        if gain <= 0:
            pool += -gain
            return
        use = min(pool, gain)
        pool -= use
        taxable = gain - use
        if lt:
            fy = _fy(dates[i])
            ex = max(0.0, exemption - fy_used.get(fy, 0.0))
            ex_used = min(ex, taxable)
            fy_used[fy] = fy_used.get(fy, 0.0) + ex_used
            t = (taxable - ex_used) * LTCG
            tax_lt += t
            gain_lt += gain
        else:
            t = taxable * STCG
            tax_st += t
            gain_st += gain
        wealth -= t

    prev = 0.0
    for i in range(len(r)):
        if w[i] == 1.0 and prev == 0.0:
            basis, entry_d = wealth, dates[i]
        wealth *= 1 + r[i]
        if w[i] == 0.0 and prev == 1.0 and basis is not None:
            settle(i)
            basis = None
        prev = w[i]
    if basis is not None:
        settle(len(r) - 1)
    yrs = years_between(pd.Series(pd.to_datetime(res["date"])))
    pre = float(np.prod(1 + r) ** (1 / yrs) - 1)
    post = float((wealth / capital) ** (1 / yrs) - 1)
    return {"cagr_pre_tax": pre, "cagr_after_tax": post, "tax_drag_pp": (pre - post) * 100, "tax_st": tax_st, "tax_lt": tax_lt,
            "episodes": n_ep, "avg_hold_days": float(np.mean(hold)) if hold else 0.0,
            "share_gain_short_term": gain_st / (gain_st + gain_lt) if gain_st + gain_lt else 0.0}


def after_tax_buyhold(res: pd.DataFrame, exemption: float = 0.0, capital: float = 1_000_000.0) -> dict:
    """B0 held to the end then sold once: long-term rate on gain above the exemption (one FY). Deferral is B0's tax advantage."""
    yrs = years_between(pd.Series(pd.to_datetime(res["date"])))
    wealth = capital * float(np.prod(1 + res["ret"].to_numpy()))
    gain = wealth - capital
    t = max(0.0, gain - exemption) * LTCG
    pre = float(np.prod(1 + res["ret"].to_numpy()) ** (1 / yrs) - 1)
    post = float(((wealth - t) / capital) ** (1 / yrs) - 1)
    return {"cagr_pre_tax": pre, "cagr_after_tax": post, "tax_drag_pp": (pre - post) * 100, "tax_lt": t}
