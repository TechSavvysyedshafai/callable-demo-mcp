"""Task 10 (Batch 5, trial B5-01): "bet against the crowd" using the put/call ratio (PCR) of option OPEN INTEREST at 09:25 on the entry day.
Rules are the literal readings in research/RESULTS.md ("Planned (pre-registered 2026-10-19, branch claude/employee-crowd ...").
Dev data only (research/data). Paper research only: nothing here places orders.

Reuses, without editing: research/wheel/wheel_core.py (index loader, the entry-timing fix `entry_day_for`, option folder),
research/ideas/forced_trader_ideas.py (bootstrap_p, null_p, Trades), research/selling/backtest.py via wheel_core (max_drawdown).
"""

from __future__ import annotations

import math
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
sys.path[:0] = [str(RESEARCH / "wheel"), str(RESEARCH / "ideas")]
import forced_trader_ideas as fi  # noqa: E402  (bootstrap_p, null_p, Trades, EPS, SEED)
import wheel_core as wc  # noqa: E402  (load_index, entry_day_for, OPT_DIR, DATA, FIRST_EXPIRY, DEV_CUTOFF, max_drawdown)

OPT_DIR, DATA, FIRST_EXPIRY, DEV_CUTOFF = wc.OPT_DIR, wc.DATA, wc.FIRST_EXPIRY, wc.DEV_CUTOFF
max_drawdown = wc.max_drawdown

TRIAL_ID, TOTAL_TRIALS = "B5-01", 15
ALPHA = 0.05 / TOTAL_TRIALS
LOT = 75  # as instructed, for rupee scale only
COST = 0.001  # 0.10% of notional per round trip
STEP = 50
WINDOW = 250  # primary strike window |K - S| <= 250
Z_THRESHOLD = 1.0
MIN_PRIOR, MAX_PRIOR = 20, 52
MIN_TRADES = 20
BLOCK, N_BOOT, N_NULL = 3, 10_000, 10_000
SIGNAL_T, ENTRY_T = time(9, 25), time(9, 30)
BAR = timedelta(minutes=5)


# ------------------------------------------------------------------------------------------------ data and weekly plans
def round50(s: float) -> int:
    """S rounded to the nearest 50, halves up."""
    return int(math.floor(s / STEP + 0.5 + 1e-9)) * STEP


def strike_grid(spot: float, half: int = WINDOW) -> list:
    """The 11 strikes the downloader fetches: R-250 .. R+250 in steps of 50, R = spot rounded to 50."""
    r = round50(spot)
    return [r + i * STEP for i in range(-half // STEP, half // STEP + 1)]


def in_window(strike: int, spot: float, half: int) -> bool:
    return abs(strike - spot) <= half + 1e-9


def make_plans(bars: pd.DataFrame, expiries: list) -> list:
    """One plan per expiry from index candles only. Signal = bar LABELLED 09:25 of the entry day (S = its close); entry = open of the bar labelled
    09:30. `skipped` is the reason a week cannot even get a signal (no entry day / no 09:25 bar / no 09:30 bar)."""
    days = sorted(set(bars["date"].dt.date))
    by_ts = bars.set_index("date")
    plans = []
    for k, ex in enumerate(expiries):
        d = wc.entry_day_for(k, expiries, days, "causal")
        p = {"k": k, "expiry": ex, "entry_day": d, "sig_ts": None, "spot": float("nan"), "skipped": None}
        if d is None:
            p["skipped"] = "no_entry_day"
        else:
            sig = datetime.combine(d, SIGNAL_T)
            ent = datetime.combine(d, ENTRY_T)
            p["sig_ts"] = pd.Timestamp(sig)
            if pd.Timestamp(sig) not in by_ts.index:
                p["skipped"] = "no_0925_bar"
            elif pd.Timestamp(ent) not in by_ts.index:
                p["skipped"] = "no_0930_bar"
            else:
                p["spot"] = float(by_ts.loc[pd.Timestamp(sig), "close"])
        plans.append(p)
    return plans


def entry_price(bars_by_ts: pd.DataFrame, plan: dict, delay: int = 0):
    """OPEN of the bar labelled 09:30 + 5 min x delay on the entry day (None if that bar does not exist)."""
    ts = pd.Timestamp(datetime.combine(plan["entry_day"], ENTRY_T)) + BAR * delay
    if ts.date() != plan["entry_day"] or ts not in bars_by_ts.index:
        return None
    return float(bars_by_ts.loc[ts, "open"])


def file_loader(opt_dir: Path | None = None):
    """loader(expiry, strike, kind) -> DataFrame indexed by candle time with columns open..oi, or None when the file is missing. Cached."""
    folder = opt_dir or OPT_DIR
    cache: dict = {}

    def load(ex, strike, kind):
        key = (ex, int(strike), kind)
        if key not in cache:
            f = folder / f"{ex.isoformat()}_{int(strike)}{kind}.csv"
            cache[key] = pd.read_csv(f, parse_dates=["date"]).set_index("date") if f.exists() else None
        return cache[key]
    return load


# ------------------------------------------------------------------------------------------------ PCR and z
def oi_at(leg, ts):
    """The `oi` field of the candle stamped exactly `ts`, or None (missing file, no such candle, empty/NaN oi). No forward fill."""
    if leg is None or ts not in leg.index or "oi" not in leg.columns:
        return None
    v = leg.loc[ts, "oi"]
    if isinstance(v, pd.Series):
        v = v.iloc[-1]
    return None if pd.isna(v) else float(v)


def pcr_of_week(plan: dict, loader, half: int = WINDOW) -> dict:
    """PCR from the strikes K with |K - S| <= half that have BOTH a call and a put OI value at the signal bar. Only candles stamped <= 09:25 are read."""
    out = {"n_strikes": 0, "call_oi": 0.0, "put_oi": 0.0, "x": None, "skipped": plan["skipped"]}
    if plan["skipped"] is not None:
        return out
    ts, ex, s = plan["sig_ts"], plan["expiry"], plan["spot"]
    for k in strike_grid(s, max(half, WINDOW)):
        if not in_window(k, s, half):
            continue
        c, p = oi_at(loader(ex, k, "CE"), ts), oi_at(loader(ex, k, "PE"), ts)
        if c is None or p is None:
            continue
        out["n_strikes"] += 1
        out["call_oi"] += c
        out["put_oi"] += p
    if out["n_strikes"] == 0:
        out["skipped"] = "no_oi_at_signal"
    elif out["call_oi"] <= 0 or out["put_oi"] <= 0:
        out["skipped"] = "zero_oi_side"
    else:
        out["pcr"] = out["put_oi"] / out["call_oi"]
        out["x"] = math.log(out["pcr"])
    return out


def zscore(history: list, x: float):
    """z of x against the previous values: at most the last MAX_PRIOR, sample sd. (None, reason) if fewer than MIN_PRIOR or sd == 0."""
    prior = history[-MAX_PRIOR:]
    if len(prior) < MIN_PRIOR:
        return None, "lt20_history"
    a = np.asarray(prior, float)
    sd = float(a.std(ddof=1))
    if sd <= 0:
        return None, "zero_sd"
    return (x - float(a.mean())) / sd, None


def signal_weeks(plans: list, loader, half: int = WINDOW) -> list:
    """Per week: PCR, x, z (using only EARLIER weeks' x), the direction (+1 long / -1 short / 0 none) and a skip reason when there is no z."""
    hist, rows = [], []
    for p in plans:
        r = {"k": p["k"], "expiry": p["expiry"], "entry_day": p["entry_day"], "spot": p["spot"]}
        r.update(pcr_of_week(p, loader, half))
        r["z"], r["direction"] = None, 0
        if r["x"] is not None:
            z, why = zscore(hist, r["x"])
            r["z"] = z
            if why:
                r["skipped"] = why
            elif z <= -Z_THRESHOLD + fi.EPS:
                r["direction"] = -1  # call-heavy: crowd bullish -> go against it
            elif z >= Z_THRESHOLD - fi.EPS:
                r["direction"] = 1  # put-heavy -> long
            hist.append(r["x"])  # own x becomes history for LATER weeks only (after z was computed)
        rows.append(r)
    return rows


# ------------------------------------------------------------------------------------------------ trades and statistics
def build_trades(plans: list, sig: list, bars_by_ts: pd.DataFrame, closes: dict, flip: bool = False, delay: int = 0, lot: int = LOT) -> dict:
    """Entry at the open of bar 09:30 + delay x 5 min; exit at the official close of the expiry day. Returns trade rows, eligible-week gross
    returns (for the null) and trade-level skips (entry bar missing for a delayed entry)."""
    trades, cand, lost = [], [], []
    for p, s in zip(plans, sig):
        if s["z"] is None:
            continue  # no z: skipped week (reason in s["skipped"]); not part of the eligible pool
        e = entry_price(bars_by_ts, p, delay)
        if e is None:
            lost.append((str(p["expiry"]), "no_entry_bar_after_delay"))
            continue
        exit_ = closes.get(p["expiry"])
        if exit_ is None:
            lost.append((str(p["expiry"]), "no_expiry_close"))
            continue
        g = exit_ / e - 1
        cand.append(g)
        if s["direction"] == 0:
            continue
        d = -s["direction"] if flip else s["direction"]
        trades.append({"k": s["k"], "expiry": p["expiry"], "entry_day": p["entry_day"], "z": s["z"], "pcr": s["pcr"], "direction": d, "entry": e,
                       "exit": exit_, "gross": g, "net_ret": d * g - COST, "gross_dir_ret": d * g,
                       "net_rs": d * (exit_ - e) * lot - COST * e * lot, "gross_rs": d * (exit_ - e) * lot})
    return {"trades": trades, "cand": cand, "lost": lost}


def to_fi_trades(tr: dict, name: str = TRIAL_ID) -> fi.Trades:
    """Wrap trades in the Batch 1 `Trades` object so bootstrap_p / null_p are the very same functions. NB: `direction` here is the trade direction."""
    t = tr["trades"]
    g = np.array([x["gross"] for x in t], float)
    return fi.Trades(15, name, np.array([np.datetime64(x["entry_day"], "D") for x in t]), np.array([x["direction"] for x in t], float), g,
                     np.zeros(len(t), int), {0: np.asarray(tr["cand"], float)}, (FIRST_EXPIRY, DEV_CUTOFF))


def evaluate(tr: dict, with_null: bool = True) -> dict:
    """All pre-registered numbers for one set of trades."""
    t = to_fi_trades(tr)
    n = len(tr["trades"])
    out = {"n_trades": n, "n_long": int(sum(x["direction"] > 0 for x in tr["trades"])), "n_short": int(sum(x["direction"] < 0 for x in tr["trades"])),
           "n_eligible_weeks": len(tr["cand"]), "lost": tr["lost"]}
    if n == 0:
        out.update({"mean_net": float("nan"), "mean_zero_cost": float("nan"), "boot_p": 1.0, "null_p": 1.0})
        out["verdict"], out["checks"] = verdict(out)
        return out
    net, gross_dir = t.net(COST), t.net(0.0)
    rs = np.array([x["net_rs"] for x in tr["trades"]])
    out.update({"mean_net": float(net.mean()), "mean_zero_cost": float(gross_dir.mean()), "median_net": float(np.median(net)),
                "win_rate": float((net > 0).mean()), "worst_trade_ret": float(net.min()), "best_trade_ret": float(net.max()),
                "worst_trade_rs": float(rs.min()), "best_trade_rs": float(rs.max()), "total_net_rs": float(rs.sum()),
                "mean_net_rs": float(rs.mean()), "max_drawdown_rs": float(max_drawdown(rs)),
                "boot_p": fi.bootstrap_p(net, block=BLOCK, n_boot=N_BOOT), "boot_p_zero_cost": fi.bootstrap_p(gross_dir, block=BLOCK, n_boot=N_BOOT),
                "worst_trade": _which(tr, rs.argmin())})
    if with_null:
        out["null_p"], out["null_mean"], out["null_q95"] = fi.null_p(t, COST, N_NULL)
        out["null_p_zero_cost"] = fi.null_p(t, 0.0, N_NULL)[0]
    else:
        out["null_p"] = float("nan")
    h = fi.halves(t, COST)
    out.update(h)
    out["halves_zero_cost"] = {k: v for k, v in fi.halves(t, 0.0).items() if k.endswith("_mean")}
    out["verdict"], out["checks"] = verdict(out)
    return out


def _which(tr: dict, i: int) -> dict:
    x = tr["trades"][int(i)]
    return {"expiry": str(x["expiry"]), "entry_day": str(x["entry_day"]), "direction": x["direction"], "entry": x["entry"], "exit": x["exit"],
            "net_ret": x["net_ret"], "net_rs": x["net_rs"]}


def verdict(r: dict, alpha: float = ALPHA):
    a = bool(r["n_trades"] > 0 and r["mean_net"] > 0)
    b = bool(r["boot_p"] < alpha)
    c = bool(r.get("null_p", 1.0) < alpha)
    d = bool(r.get("first_n", 0) > 0 and r.get("second_n", 0) > 0 and r.get("first_mean", -1) > 0 and r.get("second_mean", -1) > 0)
    e = bool(r["n_trades"] >= MIN_TRADES)
    checks = {"a_mean_net_positive": a, "b_boot_p": b, "c_null_p": c, "d_both_halves_positive": d, "e_min_20_trades": e}
    if a and b and c and d and e:
        return "SURVIVES", checks
    if a and r["boot_p"] < 0.05:
        return "INCONCLUSIVE", checks
    return "REJECT", checks


def skip_summary(sig: list) -> dict:
    """Count and list every week with no z (no trade possible), by reason."""
    by: dict = {}
    for s in sig:
        if s["z"] is None:
            by.setdefault(s["skipped"] or "unknown", []).append(str(s["expiry"]))
    return {"n_weeks": len(sig), "n_with_z": sum(s["z"] is not None for s in sig), "n_skipped": sum(len(v) for v in by.values()),
            "by_reason": {k: {"n": len(v), "weeks": v} for k, v in sorted(by.items())}}
