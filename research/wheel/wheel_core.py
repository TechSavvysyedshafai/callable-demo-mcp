"""Task 8 (Batch 4): the "wheel" (cash-secured put -> covered call -> repeat) on NIFTY, as an INDEX PROXY on real expired weekly option candles.
Rules are the literal readings in research/RESULTS.md ("Planned (pre-registered 2026-10-18, branch claude/employee-wheel ...").
Dev data only (research/data). Paper research only: nothing here places orders.

Reuses, without editing: research/selling/backtest.py (strike rounding, entry day/bar, option-file loader, settlement STT, drawdown),
research/scalp/options/costs_opt.py (option fees), research/ideas/forced_trader_ideas.py (bootstrap_p, same block bootstrap as Batch 1).
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
sys.path[:0] = [str(RESEARCH / "ideas"), str(RESEARCH / "scalp" / "options")]
import forced_trader_ideas as fi  # noqa: E402  (bootstrap_p)
from costs_opt import OptionCostModel  # noqa: E402


def _load_selling():
    # research/selling/backtest.py has a generic name; load it under a unique alias so nothing else called `backtest` is shadowed.
    spec = importlib.util.spec_from_file_location("selling_wheel_logic", RESEARCH / "selling" / "backtest.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["selling_wheel_logic"] = m
    spec.loader.exec_module(m)
    return m


sb = _load_selling()
short_strikes = sb.short_strikes  # (call rounded UP, put rounded DOWN)
intrinsic = sb.intrinsic
max_drawdown = sb.max_drawdown
OPT_DIR, DATA, DEV_CUTOFF, FIRST_EXPIRY = sb.OPT_DIR, sb.DATA, sb.DEV_CUTOFF, sb.FIRST_EXPIRY

LOT = 75  # as instructed; unverified for the whole window
SETTLE_STT = sb.SETTLE_STT  # 0.15% of intrinsic on an in-the-money cash-settled leg
EXPO_COST = 0.00065  # 0.065% of notional per assignment / per called-away event / benchmark entry / benchmark exit (all-in)
CASH_RATE = 0.065
SLIPS = (0.10, 0.20, 0.30)
DECISION_SLIP = 0.20
TOTAL_TRIALS = 14
ALPHA = 0.05 / TOTAL_TRIALS
CASH, LONG = "CASH", "LONG"
MODES = ("wheel", "put_only", "call_only")


# ------------------------------------------------------------------------------------------------ data and entry plans
def load_index():
    """(5-minute bars, {date: official daily close}, dev expiries from 2024-10-03 to 2026-04-16)."""
    bars = pd.read_csv(DATA / "nifty_5minute_dev.csv", parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    daily = pd.read_csv(DATA / "nifty_day_dev.csv", parse_dates=["date"])
    closes = {d.date(): float(c) for d, c in zip(daily["date"], daily["close"])}
    ex = pd.read_csv(DATA / "nifty_expiries.csv")["expiry"].tolist()
    expiries = sorted(date.fromisoformat(x) for x in ex if FIRST_EXPIRY <= date.fromisoformat(x) <= DEV_CUTOFF)
    return bars, closes, expiries


def entry_day_for(k: int, expiries: list, days: list, timing: str = "causal"):
    """Entry day of week k. timing "as_written": research/selling rule (nearest trading day on or before expiry-7d), which for a normal week is the
    previous expiry's own day, i.e. BEFORE it settles (diagnostic only: using it means knowing the settlement). timing "causal": the LATER of that day and
    the first trading day strictly after the previous expiry's day (week 0: the selling rule)."""
    a = sb.entry_day(expiries[k], days)
    if timing == "as_written" or k == 0:
        return a
    after = [d for d in days if d > expiries[k - 1]]
    b = min(after) if after else None
    if a is None:
        return b
    return max(a, b) if b is not None else a


def make_plans(bars: pd.DataFrame, expiries: list, shift: int = 0, timing: str = "causal") -> list:
    """One plan per expiry using ONLY the entry bar's candle (timestamp, close = spot). e_idx None => no entry bar."""
    days = sorted(set(bars["date"].dt.date))
    plans = []
    for k, ex in enumerate(expiries):
        d = entry_day_for(k, expiries, days, timing)
        e = sb.entry_bar(bars, d, shift) if d else None
        p = {"k": k, "expiry": ex, "entry_day": d, "ts": None, "spot": float("nan"), "put_k": None, "call_k": None}
        if e is not None:
            spot = float(bars.loc[e, "close"])
            call, put = short_strikes(spot)
            p.update(ts=bars.loc[e, "date"].to_pydatetime(), spot=spot, put_k=put, call_k=call)
        plans.append(p)
    return plans


def needed_contracts(bars: pd.DataFrame, expiries: list) -> set:
    """(expiry, strike, kind) for every put and call any run can need: causal timing at shifts 0, +1, +2 and the as-written diagnostic at shift 0."""
    need = set()
    for timing, shift in (("causal", 0), ("causal", 1), ("causal", 2), ("as_written", 0)):
        for p in make_plans(bars, expiries, shift, timing):
            if p["ts"] is not None:
                need.add((p["expiry"], p["put_k"], "PE"))
                need.add((p["expiry"], p["call_k"], "CE"))
    return need


# ------------------------------------------------------------------------------------------------ the weekly engine
def benchmark_weekly(plans: list, closes: dict, lot: int = LOT) -> list:
    """Buy at the close of the first entry bar, hold to the last official close, 0.065% of notional at each end; marked at official closes."""
    first = plans[0]["spot"]
    out, prev = [], first
    for i, p in enumerate(plans):
        s = closes[p["expiry"]]
        v = (s - prev) * lot
        if i == 0:
            v -= EXPO_COST * first * lot
        if i == len(plans) - 1:
            v -= EXPO_COST * s * lot
        out.append(v)
        prev = s
    return out


def run_weeks(plans: list, closes: dict, loader, slip: float, mode: str = "wheel", lot: int = LOT, cm_kwargs: dict | None = None) -> list:
    """Simulate `mode` week by week. `loader(expiry, strike, kind)` -> DataFrame indexed by candle time with an "open" column, or None.
    The leg sold in week k is chosen from the state at the START of week k, which is set only by settlements of earlier expiries."""
    assert mode in MODES
    cm = OptionCostModel(slippage_rs=slip, **(cm_kwargs or {}))
    first = plans[0]["spot"]
    bench = benchmark_weekly(plans, closes, lot)
    state = LONG if mode == "call_only" else CASH
    prev_mark = first
    rows = []
    for i, p in enumerate(plans):
        ex, last_week = p["expiry"], i == len(plans) - 1
        settle = closes[ex]
        start = state
        days = (ex - (p["entry_day"] if i == 0 else plans[i - 1]["expiry"])).days
        r = {"k": i, "expiry": ex, "entry_day": p["entry_day"], "entry_ts": p["ts"], "spot": p["spot"], "state_start": start, "settle": settle,
             "kind": None, "strike": None, "fill": float("nan"), "skipped": None, "premium_rs": 0.0, "fees_rs": 0.0, "intrinsic_rs": 0.0,
             "stt_rs": 0.0, "exposure_mark_rs": 0.0, "expo_cost_rs": 0.0, "event": None}
        if start == LONG:
            r["exposure_mark_rs"] = (settle - prev_mark) * lot
            if mode == "call_only" and i == 0:
                r["expo_cost_rs"] += EXPO_COST * first * lot
        kind = "CE" if start == LONG else "PE"
        r["kind"] = kind
        if p["ts"] is None:
            r["skipped"] = "no_entry_bar"
        else:
            strike = p["call_k"] if kind == "CE" else p["put_k"]
            r["strike"] = strike
            leg = loader(ex, strike, kind)
            if leg is None:
                r["skipped"] = "missing_option_file"
            elif p["ts"] not in leg.index:
                r["skipped"] = "no_candle_at_entry"
            else:
                fill = max(float(leg.loc[p["ts"], "open"]) - slip, 0.0)
                r["fill"] = fill
                if fill <= 0:
                    r["skipped"] = "nonpositive_fill"
        if r["skipped"] is None:
            iv = intrinsic(kind, r["strike"], settle)
            r["premium_rs"] = r["fill"] * lot
            r["fees_rs"] = cm.side(r["fill"], lot, is_buy=False)
            r["intrinsic_rs"] = iv * lot
            r["stt_rs"] = SETTLE_STT * iv * lot
            if mode == "wheel":
                if start == CASH and settle < r["strike"]:
                    state, r["event"] = LONG, "assigned"
                    r["expo_cost_rs"] += EXPO_COST * r["strike"] * lot
                elif start == LONG and settle > r["strike"]:
                    state, r["event"] = CASH, "called_away"
                    r["expo_cost_rs"] += EXPO_COST * r["strike"] * lot
            elif iv > 0:
                r["event"] = "assigned" if kind == "PE" else "called_away"
        if last_week and state == LONG:  # liquidate any open exposure at the last official close, like the benchmark's exit
            r["expo_cost_rs"] += EXPO_COST * settle * lot
        r["state_end"] = state
        r["net_rs"] = r["premium_rs"] - r["fees_rs"] - r["intrinsic_rs"] - r["stt_rs"] + r["exposure_mark_rs"] - r["expo_cost_rs"]
        r["bench_rs"] = bench[i]
        r["d_rs"] = r["net_rs"] - bench[i]
        r["cash_info_rs"] = CASH_RATE * days / 365 * first * lot if start == CASH else 0.0
        rows.append(r)
        prev_mark = settle
    return rows


# ------------------------------------------------------------------------------------------------ statistics
def halves_of(rows: list, series: list) -> dict:
    """Split at the calendar midpoint between the first and last expiry date (expiry <= midpoint = first half)."""
    lo, hi = pd.Timestamp(rows[0]["expiry"]), pd.Timestamp(rows[-1]["expiry"])
    mid = lo + (hi - lo) / 2
    first = np.array([pd.Timestamp(r["expiry"]) <= mid for r in rows])
    x = np.asarray(series, float)
    return {"midpoint": str(mid.date()), "first_n": int(first.sum()), "second_n": int((~first).sum()),
            "first_mean": float(x[first].mean()) if first.any() else float("nan"),
            "second_mean": float(x[~first].mean()) if (~first).any() else float("nan")}


def series_stats(x) -> dict:
    x = np.asarray(x, float)
    sd = float(x.std(ddof=1)) if len(x) > 1 else float("nan")
    return {"total": float(x.sum()), "mean": float(x.mean()), "median": float(np.median(x)), "worst_week": float(x.min()), "best_week": float(x.max()),
            "max_drawdown": float(max_drawdown(x)), "std": sd, "sharpe_like": float(x.mean() / sd) if sd and sd > 0 else float("nan")}


def verdict_of(mean_d: float, p: float, dd_wheel: float, dd_bench: float, first_mean: float, second_mean: float, alpha: float = ALPHA):
    a = bool(mean_d > 0)
    b = bool(p < alpha)
    c = bool(abs(dd_wheel) < abs(dd_bench))
    d = bool(first_mean > 0 and second_mean > 0)
    checks = {"a_mean_D_positive": a, "b_boot_p": b, "c_smaller_drawdown": c, "d_both_halves_positive": d}
    if a and b and c and d:
        return "SURVIVES", checks
    if a and b:
        return "INCONCLUSIVE", checks
    return "REJECT", checks


def summarise(rows: list, notional: float) -> dict:
    """All pre-registered numbers for one run (D is vs the benchmark in the same rows)."""
    net = [r["net_rs"] for r in rows]
    ben = [r["bench_rs"] for r in rows]
    d = [r["d_rs"] for r in rows]
    skipped = [r for r in rows if r["skipped"] is not None]
    traded = [r for r in rows if r["skipped"] is None]
    s, sb_, sd = series_stats(net), series_stats(ben), series_stats(d)
    h = halves_of(rows, d)
    p = fi.bootstrap_p(np.asarray(d, float))
    v, checks = verdict_of(sd["mean"], p, s["max_drawdown"], sb_["max_drawdown"], h["first_mean"], h["second_mean"])
    out = {"n_weeks": len(rows), "n_traded": len(traded), "n_skipped": len(skipped),
           "skipped": [(str(r["expiry"]), r["state_start"], r["skipped"]) for r in skipped],
           "wheel": s, "bench": sb_, "D": sd, "boot_p": p, "halves": h, "verdict": v, "checks": checks,
           "total_return_wheel": s["total"] / notional, "total_return_bench": sb_["total"] / notional,
           "weeks_start_cash": sum(r["state_start"] == CASH for r in rows), "weeks_start_long": sum(r["state_start"] == LONG for r in rows),
           "assignments": sum(r["event"] == "assigned" for r in rows), "called_away": sum(r["event"] == "called_away" for r in rows),
           "premium_rs": float(sum(r["premium_rs"] for r in rows)), "intrinsic_paid_rs": float(sum(r["intrinsic_rs"] for r in rows)),
           "exposure_marks_rs": float(sum(r["exposure_mark_rs"] for r in rows)), "option_fees_rs": float(sum(r["fees_rs"] for r in rows)),
           "settle_stt_rs": float(sum(r["stt_rs"] for r in rows)), "exposure_costs_rs": float(sum(r["expo_cost_rs"] for r in rows)),
           "idle_cash_info_rs": float(sum(r["cash_info_rs"] for r in rows)), "notional": notional}
    out["wheel_plus_idle_cash_total"] = s["total"] + out["idle_cash_info_rs"]
    return out
