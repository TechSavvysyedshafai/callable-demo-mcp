"""Batch 6 (B6-01): gold vs silver ratio pair trade on the NSE ETFs GOLDBEES and SILVERBEES. Rules exactly as written in
docs/ideas/IDEAS_BATCH6_GOLD_SILVER_PAIR_2026-10-19.md; readings of ambiguous rules are in research/RESULTS.md
("Planned (pre-registered 2026-10-19, branch claude/employee-goldsilver ...").

Everything is in fractions of ONE leg's notional (the two legs have equal rupee notional at entry):
  gross = direction x [(gold exit open / gold entry open - 1) - (silver exit open / silver entry open - 1)]
  direction +1 = buy gold, sell silver (Z <= -entry); direction -1 = sell gold, buy silver (Z >= +entry).
Dev data only (to 2026-04-16). Nothing here reads the hidden holdout or places orders.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
sys.path.insert(0, str(RESEARCH / "ideas"))
import forced_trader_ideas as fi  # noqa: E402  (bootstrap_p, SEED: imported, not edited)

DATA = RESEARCH / "data"
CUTOFF = pd.Timestamp(date(2026, 4, 16))
LOOKBACK, ENTRY, EXIT, STOP, MAX_HOLD = 60, 2.0, 0.5, 4.0, 20
COST_RT = 0.002  # 0.10% per leg round trip, two legs, as a fraction of one-leg notional
FIN_PER_DAY = 0.0002  # 0.02% per day held on the short leg (assumption; unverified)
ALPHA = 0.05 / 16
MIN_TRADES = 15
BLOCK, N_BOOT, N_NULL, SEED = 3, 10_000, 10_000, fi.SEED
EPS = 1e-12


# ----------------------------------------------------------------------------------------------- data
def _read(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path, parse_dates=["date"])
    d["date"] = d["date"].dt.normalize()
    d = d[d["date"] <= CUTOFF]
    return d.drop_duplicates().sort_values("date").reset_index(drop=True)


def load(gold_path: Path | None = None, silver_path: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """Common-calendar frame (date, g_open, g_close, s_open, s_close) and the skipped-day accounting."""
    g = _read(gold_path or DATA / "goldbees_day_dev.csv")
    s = _read(silver_path or DATA / "silverbees_day_dev.csv")
    first_s = s["date"].min()
    g_after = g[g["date"] >= first_s]
    only_g = sorted(set(g_after["date"]) - set(s["date"]))
    only_s = sorted(set(s["date"]) - set(g_after["date"]))
    m = g.merge(s, on="date", suffixes=("_g", "_s"))
    bad = ~((m[["open_g", "close_g", "open_s", "close_s"]] > 0).all(axis=1))  # also catches NaN (comparison is False)
    skipped = {"only_gold": [str(x.date()) for x in only_g], "only_silver": [str(x.date()) for x in only_s],
               "bad_price_rows": [str(x.date()) for x in m.loc[bad, "date"]],
               "zero_volume_days": int(((m["volume_g"] == 0) | (m["volume_s"] == 0)).sum()),
               "gold_rows_before_silver_listed": int((g["date"] < first_s).sum()),
               "silver_first_date": str(first_s.date()), "last_date": str(m["date"].max().date())}
    m = m[~bad]
    out = pd.DataFrame({"date": m["date"], "g_open": m["open_g"], "g_close": m["close_g"], "s_open": m["open_s"], "s_close": m["close_s"]})
    out = out.reset_index(drop=True)
    skipped["n_skipped_days"] = len(only_g) + len(only_s) + int(bad.sum())
    skipped["n_common_days"] = len(out)
    assert out["date"].max() <= CUTOFF
    return out, skipped


# ----------------------------------------------------------------------------------------------- signal
def zscore(g_close: np.ndarray, s_close: np.ndarray, lookback: int = LOOKBACK) -> np.ndarray:
    """Z_t = (r_t - mean r[t-lb+1..t]) / std r[t-lb+1..t] (ddof 1), r = ln(gold close / silver close). The window ENDS at t and
    includes t. NaN for the first lb-1 rows and when the window std is zero."""
    r = np.log(np.asarray(g_close, float) / np.asarray(s_close, float))
    z = np.full(len(r), np.nan)
    for t in range(lookback - 1, len(r)):
        w = r[t - lookback + 1: t + 1]
        sd = w.std(ddof=1)
        if sd > 0:
            z[t] = (r[t] - w.mean()) / sd
    return z


# ----------------------------------------------------------------------------------------------- the rule
def simulate(df: pd.DataFrame, lookback: int = LOOKBACK, entry: float = ENTRY, exit_: float = EXIT, stop: float = STOP,
             max_hold: int = MAX_HOLD) -> dict:
    """Walk the calendar once. Returns trades (list of dicts) plus counts of skipped signals and unfinished trades."""
    go, so = df["g_open"].to_numpy(float), df["s_open"].to_numpy(float)
    dates = df["date"].to_numpy("datetime64[D]")
    z = zscore(df["g_close"].to_numpy(float), df["s_close"].to_numpy(float), lookback)
    n = len(df)
    trades, skipped_signals, unfinished = [], 0, 0
    i = lookback - 1
    while i < n:
        zi = z[i]
        if np.isnan(zi):
            i += 1
            continue
        if zi >= entry - EPS:
            direction = -1  # gold expensive vs silver: sell gold, buy silver
        elif zi <= -entry + EPS:
            direction = +1  # gold cheap: buy gold, sell silver
        else:
            i += 1
            continue
        e = i + 1  # entry at the NEXT row's open
        if e >= n:
            skipped_signals += 1
            break
        exit_row, reason, c = None, None, e
        for k in range(max_hold):
            c = e + k
            if c >= n:
                break
            zc = z[c]
            if abs(zc) <= exit_ + EPS:
                exit_row, reason = c + 1, "revert"
            elif abs(zc) >= stop - EPS:
                exit_row, reason = c + 1, "stop"
            elif k == max_hold - 1:
                exit_row, reason = e + max_hold, "time"
            if exit_row is not None:
                break
        if exit_row is None or exit_row >= n:  # data ends before the exit open exists
            unfinished += 1
            break
        gross = direction * ((go[exit_row] / go[e] - 1) - (so[exit_row] / so[e] - 1))
        cal = int((dates[exit_row] - dates[e]).astype(int))
        trades.append({"signal_row": i, "entry_row": e, "exit_row": exit_row, "direction": direction, "reason": reason,
                       "z_signal": float(zi), "hold": exit_row - e, "cal_days": cal, "gross": float(gross),
                       "signal_date": str(dates[i]), "entry_date": str(dates[e]), "exit_date": str(dates[exit_row])})
        i = exit_row  # the earliest new signal is the close of the exit-open day
    return {"trades": trades, "skipped_signals": skipped_signals, "unfinished": unfinished, "z": z}


# ----------------------------------------------------------------------------------------------- costs and statistics
def trade_cost(cal_days, hold, financing: str = "calendar", cost_rt: float = COST_RT, fin: float = FIN_PER_DAY):
    days = np.asarray(cal_days if financing == "calendar" else hold, float)
    return cost_rt + fin * days


def net_returns(trades: list, zero_cost: bool = False, financing: str = "calendar") -> np.ndarray:
    if not trades:
        return np.zeros(0)
    gross = np.array([t["gross"] for t in trades])
    if zero_cost:
        return gross
    return gross - trade_cost([t["cal_days"] for t in trades], [t["hold"] for t in trades], financing)


def max_drawdown(net: np.ndarray) -> float:
    """Largest peak-to-trough fall of the running sum of per-trade nets (<= 0), in fractions of one-leg notional."""
    if len(net) == 0:
        return 0.0
    cum = np.concatenate([[0.0], np.cumsum(net)])
    return float((cum - np.maximum.accumulate(cum)).min())


def halves(trades: list, net: np.ndarray, lo, hi) -> dict:
    lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
    mid = lo + (hi - lo) / 2
    when = pd.to_datetime([t["entry_date"] for t in trades])
    first = np.asarray(when <= mid)
    out = {"midpoint": str(mid.date())}
    for name, mk in (("first", first), ("second", ~first)):
        out[name + "_n"] = int(mk.sum())
        out[name + "_mean"] = float(net[mk].mean()) if mk.any() else float("nan")
    return out


def null_candidates(df: pd.DataFrame, h: int, first_entry: int, financing: str = "calendar", cost_rt: float = COST_RT,
                    fin: float = FIN_PER_DAY) -> tuple:
    """Every possible entry row from first_entry with an exit open h rows later: (long-gold gross, cost) per candidate."""
    go, so = df["g_open"].to_numpy(float), df["s_open"].to_numpy(float)
    dates = df["date"].to_numpy("datetime64[D]")
    s = np.arange(first_entry, len(df) - h)
    gross = (go[s + h] / go[s] - 1) - (so[s + h] / so[s] - 1)
    days = (dates[s + h] - dates[s]).astype(int) if financing == "calendar" else np.full(len(s), h)
    return gross, cost_rt + fin * days


def gs_null_p(df: pd.DataFrame, trades: list, first_entry: int, n_draw: int = N_NULL, seed: int = SEED, chunk: int = 500,
              financing: str = "calendar", cost_rt: float = COST_RT, fin: float = FIN_PER_DAY) -> tuple:
    """Random-date null with the draw logic of forced_trader_ideas.null_p (same seed, same order) but a per-candidate cost
    (financing depends on the calendar days of the random dates). Same number of trades per holding length and same long/short mix."""
    n_tot = len(trades)
    if n_tot == 0:
        return 1.0, 0.0, 0.0
    hold = np.array([t["hold"] for t in trades])
    direction = np.array([t["direction"] for t in trades])
    cal = [t["cal_days"] for t in trades]
    obs = float(np.mean([t["gross"] for t in trades]) - np.mean(trade_cost(cal, hold, financing, cost_rt, fin)))
    rng = np.random.default_rng(seed)
    stat = np.zeros(n_draw)
    for key in np.unique(hold):
        dirs = direction[hold == key]
        n_long, n_short = int((dirs > 0).sum()), int((dirs < 0).sum())
        gross, cost = null_candidates(df, int(key), first_entry, financing, cost_rt, fin)
        M = len(gross)
        n = min(n_long + n_short, M)
        n_long = min(n_long, n)
        net_long, net_short = gross - cost, -gross - cost
        for a in range(0, n_draw, chunk):
            r = rng.random((min(chunk, n_draw - a), M))
            idx = np.argsort(r, axis=1)[:, :n]
            stat[a:a + len(idx)] += net_long[idx[:, :n_long]].sum(axis=1) + net_short[idx[:, n_long:n]].sum(axis=1)
    nul = stat / n_tot
    p = float((1 + np.sum(nul >= obs - 1e-15)) / (n_draw + 1))
    return p, float(nul.mean()), float(np.quantile(nul, 0.95))


# ----------------------------------------------------------------------------------------------- one full evaluation
def evaluate(df: pd.DataFrame, lookback: int = LOOKBACK, entry: float = ENTRY, with_null: bool = True) -> dict:
    sim = simulate(df, lookback, entry)
    tr = sim["trades"]
    net, gross = net_returns(tr), net_returns(tr, zero_cost=True)
    lo, hi = df["date"].iloc[0], df["date"].iloc[-1]
    res = {"lookback": lookback, "entry": entry, "n_trades": len(tr), "skipped_signals": sim["skipped_signals"], "unfinished": sim["unfinished"],
           "mean_net": float(net.mean()) if len(net) else float("nan"), "mean_gross": float(gross.mean()) if len(net) else float("nan"),
           "median_net": float(np.median(net)) if len(net) else float("nan"),
           "win_rate": float((net > 0).mean()) if len(net) else float("nan"),
           "worst_net": float(net.min()) if len(net) else float("nan"), "best_net": float(net.max()) if len(net) else float("nan"),
           "max_drawdown": max_drawdown(net), "total_net": float(net.sum()),
           "mean_hold": float(np.mean([t["hold"] for t in tr])) if tr else float("nan"),
           "exit_reasons": {k: int(sum(t["reason"] == k for t in tr)) for k in ("revert", "stop", "time")},
           "n_long_gold": int(sum(t["direction"] > 0 for t in tr)), "n_short_gold": int(sum(t["direction"] < 0 for t in tr)),
           "boot_p": fi.bootstrap_p(net, BLOCK, N_BOOT, SEED), "boot_p_zero_cost": fi.bootstrap_p(gross, BLOCK, N_BOOT, SEED)}
    res.update(halves(tr, net, lo, hi))
    res["halves_zero_cost"] = {k: v for k, v in halves(tr, gross, lo, hi).items() if k.endswith("_mean")}
    first_entry = lookback  # first row a real signal could enter on (first Z is at row lookback-1)
    res["tradable_halves"] = halves(tr, net, df["date"].iloc[first_entry], hi)
    if with_null and tr:
        res["null_p"], res["null_mean"], res["null_q95"] = gs_null_p(df, tr, first_entry)
        res["null_p_zero_cost"] = gs_null_p(df, tr, first_entry, cost_rt=0.0, fin=0.0)[0]
    else:
        res["null_p"] = res["null_mean"] = res["null_q95"] = res["null_p_zero_cost"] = float("nan")
    net_td = net_returns(tr, financing="trading")
    res["mean_net_trading_day_financing"] = float(net_td.mean()) if len(net_td) else float("nan")
    res["checks"], res["verdict"] = verdict(res)
    return res


def verdict(r: dict) -> tuple:
    a = bool(r["n_trades"] > 0 and r["mean_net"] > 0)
    b = bool(r["boot_p"] < ALPHA)
    c = bool(r["null_p"] < ALPHA)  # NaN compares False
    d_ = bool(r["first_n"] > 0 and r["second_n"] > 0 and r["first_mean"] > 0 and r["second_mean"] > 0)
    e = bool(r["n_trades"] >= MIN_TRADES)
    checks = {"a_trades_ge_15": e, "b_mean_net_positive": a, "c_boot_p": b, "d_both_halves_positive": d_, "e_null_p": c}
    if not e:
        return checks, "INCONCLUSIVE"
    return checks, "PASS" if (a and b and c and d_) else "REJECT"
