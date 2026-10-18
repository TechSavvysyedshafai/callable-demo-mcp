"""Task 7 (Batch 3, "settlement mechanics"): all the arithmetic for gate G0 and trials T1, T2, T3.
Rules are the literal readings written in research/RESULTS.md ("Planned (pre-registered 2026-10-18, branch claude/employee-settlement ...").
Dev data only (research/data). Paper research only: nothing here places orders.

Reuses, without editing: research/selling/backtest.py (intrinsic, settlement STT, drawdown, option-file loader),
research/scalp/options/costs_opt.py (fees), research/ideas/forced_trader_ideas.py (bootstrap_p, same block bootstrap as Batch 1).
"""

from __future__ import annotations

import importlib.util
import math
import sys
from datetime import date, datetime, time
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
    spec = importlib.util.spec_from_file_location("selling_settle_logic", RESEARCH / "selling" / "backtest.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["selling_settle_logic"] = m
    spec.loader.exec_module(m)
    return m


sb = _load_selling()
intrinsic = sb.intrinsic
settlement_stt = sb.settlement_stt
max_drawdown = sb.max_drawdown
load_leg = sb.load_leg
OPT_DIR = sb.OPT_DIR
DATA = sb.DATA
DEV_CUTOFF = sb.DEV_CUTOFF
FIRST_EXPIRY = sb.FIRST_EXPIRY

LOT = 75  # as instructed; unverified for the whole window
STEP = 50
WING = 100
SLIPS = (0.10, 0.20, 0.30)
DECISION_SLIP = 0.20
TOTAL_TRIALS = 13
ALPHA = 0.05 / TOTAL_TRIALS
MIN_TRADES = 60
GATE_MAX_RATIO = 0.85
T_DECISION = time(15, 0)
T_LAST = time(15, 25)
T_OI = time(14, 50)  # last bar COMPLETED at 14:55
SCAN = 500
BARS_IN_WINDOW = 6  # 15:00-15:30 in 5-minute bars
N_DRAW, SEED = 10_000, 20261018


# ------------------------------------------------------------------------------------------------ data
def load_index():
    """(5-minute bars, {date: official daily close}, dev expiries from 2024-10-03 to 2026-04-16)."""
    bars = pd.read_csv(DATA / "nifty_5minute_dev.csv", parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    daily = pd.read_csv(DATA / "nifty_day_dev.csv", parse_dates=["date"])
    closes = {d.date(): float(c) for d, c in zip(daily["date"], daily["close"])}
    ex = pd.read_csv(DATA / "nifty_expiries.csv")["expiry"].tolist()
    expiries = sorted(date.fromisoformat(x) for x in ex if FIRST_EXPIRY <= date.fromisoformat(x) <= DEV_CUTOFF)
    return bars, closes, expiries


def day_frame(bars: pd.DataFrame, day: date) -> pd.DataFrame:
    """Bars of one day indexed by their label time (datetime.time)."""
    d = bars[bars["date"].dt.date == day]
    return d.set_index(d["date"].dt.time)


def round_strike(s0: float) -> int:
    """Nearest multiple of 50, halves rounded up."""
    return int(math.floor(s0 / STEP + 0.5)) * STEP


def s0_s1(frame: pd.DataFrame):
    """(S0, S1) = (open of the 15:00 bar, close of the 15:25 bar), or None if either bar is missing."""
    if T_DECISION not in frame.index or T_LAST not in frame.index:
        return None
    return float(frame.loc[T_DECISION, "open"]), float(frame.loc[T_LAST, "close"])


# ------------------------------------------------------------------------------------------------ G0
def gate_g0(bars: pd.DataFrame, closes: dict, expiries: list) -> dict:
    a_minus_s0, s1_minus_s0, used, skipped = [], [], [], []
    for ex in expiries:
        f = day_frame(bars, ex)
        pair = s0_s1(f)
        if pair is None:
            skipped.append((ex, "no_1500_or_1525_bar"))
            continue
        if ex not in closes:
            skipped.append((ex, "no_daily_close"))
            continue
        s0, s1 = pair
        a_minus_s0.append(closes[ex] - s0)
        s1_minus_s0.append(s1 - s0)
        used.append(ex)
    a, b = np.array(a_minus_s0), np.array(s1_minus_s0)
    sa, sb_ = (float(np.std(a, ddof=1)), float(np.std(b, ddof=1))) if len(a) > 1 else (float("nan"), float("nan"))
    ratio = sa / sb_ if sb_ else float("nan")
    return {"n": len(a), "std_A_minus_S0": sa, "std_S1_minus_S0": sb_, "ratio": ratio, "stop": bool(ratio > GATE_MAX_RATIO),
            "mean_A_minus_S0": float(a.mean()) if len(a) else float("nan"), "mean_S1_minus_S0": float(b.mean()) if len(b) else float("nan"),
            "skipped": skipped, "days": used}


# ------------------------------------------------------------------------------------------------ T1 / T2
def leg_open(leg: pd.DataFrame | None, ts: datetime) -> float | None:
    """Open of the candle labelled ts, or None when the file/candle is missing or the open is not positive."""
    if leg is None or ts not in leg.index:
        return None
    px = float(leg.loc[ts, "open"])
    return px if px > 0 and px == px else None


def sigma_points(frame: pd.DataFrame) -> float:
    """Sample std of the day's 5-minute close-to-close changes (points) using bars labelled before 15:00 (all closed by 15:00)."""
    c = frame.loc[[t for t in frame.index if t < T_DECISION], "close"].to_numpy(float)
    return float(np.std(np.diff(c), ddof=1)) if len(c) > 2 else float("nan")


def model_asian_straddle(sigma_pts: float, normal_factor: bool = False) -> float:
    """(1/sqrt(3)) * sigma * sqrt(6): the std of (average - S0) over the last 30 minutes. With normal_factor, times sqrt(2/pi), the value
    of an at-the-money straddle on a zero-mean normal outcome."""
    v = sigma_pts * math.sqrt(BARS_IN_WINDOW) / math.sqrt(3)
    return v * math.sqrt(2 / math.pi) if normal_factor else v


def leg_defs(k: int, wings: bool) -> dict:
    """name -> (strike, kind, is_buy)."""
    d = {"sc": (k, "CE", False), "sp": (k, "PE", False)}
    if wings:
        d["lc"] = (k + WING, "CE", True)
        d["lp"] = (k - WING, "PE", True)
    return d


def price_trade(opens: dict, defs: dict, settle: float, slip: float, cm: OptionCostModel | None, fees: bool = True) -> dict:
    """One straddle (or wing-protected straddle) held to settlement. opens: name -> open price at 15:00. Per-unit points and rupees (LOT units)."""
    cm = cm or OptionCostModel(slippage_rs=slip)
    fills = {n: max(opens[n] + (slip if defs[n][2] else -slip), 0.0) for n in defs}
    intr = {n: intrinsic(defs[n][1], defs[n][0], settle) for n in defs}
    pts = sum((-1 if defs[n][2] else 1) * fills[n] for n in defs) - sum((-1 if defs[n][2] else 1) * intr[n] for n in defs)
    st = {n: (defs[n][0], defs[n][1]) for n in defs}
    entry_fees = sum(cm.side(fills[n], LOT, is_buy=defs[n][2]) for n in defs) if fees else 0.0
    settle_stt = settlement_stt(st, settle, LOT) if fees else 0.0
    return {"pts": pts, "entry_fees": entry_fees, "settle_stt": settle_stt, "net_rs": pts * LOT - entry_fees - settle_stt, "gross_rs": pts * LOT}


def run_straddle_trial(bars, closes, expiries, wings: bool) -> dict:
    """T1 (wings=False) or T2 (wings=True). Returns per-day rows (with net Rs at each slippage) and the skipped list with reasons."""
    rows, skipped = [], []
    for ex in expiries:
        f = day_frame(bars, ex)
        pair = s0_s1(f)
        if pair is None:
            skipped.append((ex, "no_1500_or_1525_bar"))
            continue
        if ex not in closes:
            skipped.append((ex, "no_daily_close"))
            continue
        s0 = pair[0]
        k = round_strike(s0)
        defs = leg_defs(k, wings)
        legs = {n: load_leg(ex, s, kind) for n, (s, kind, _) in defs.items()}
        if any(v is None for v in legs.values()):
            skipped.append((ex, "missing_option_file"))
            continue
        ts = datetime.combine(ex, T_DECISION)
        opens = {n: leg_open(legs[n], ts) for n in defs}
        if any(v is None for v in opens.values()):
            skipped.append((ex, "missing_candle_at_1500"))
            continue
        settle = closes[ex]
        row = {"expiry": ex, "S0": s0, "K": k, "A": settle, "S1": pair[1], "straddle_px": opens["sc"] + opens["sp"],
               "sigma_pts": sigma_points(f), "opens": opens}
        row["gross_mid_rs"] = price_trade(opens, defs, settle, 0.0, None, fees=False)["gross_rs"]
        for s in SLIPS:
            r = price_trade(opens, defs, settle, s, OptionCostModel(slippage_rs=s))
            row[f"net_{s:.2f}"], row[f"fees_{s:.2f}"] = r["net_rs"], r["entry_fees"] + r["settle_stt"]
        rows.append(row)
    return {"rows": rows, "skipped": skipped}


def halves_means(dates: list, net: np.ndarray) -> dict:
    """Same split as forced_trader_ideas.halves: calendar midpoint between first and last traded day."""
    if len(dates) == 0:
        return {"first_n": 0, "second_n": 0, "first_mean": float("nan"), "second_mean": float("nan"), "midpoint": None}
    ts = pd.to_datetime(pd.Series(dates))
    mid = ts.min() + (ts.max() - ts.min()) / 2
    first = (ts <= mid).to_numpy()
    out = {"midpoint": str(mid.date())}
    for name, mk in (("first", first), ("second", ~first)):
        out[name + "_n"] = int(mk.sum())
        out[name + "_mean"] = float(net[mk].mean()) if mk.any() else float("nan")
    return out


def verdict(mean_net: float, boot_p: float, n: int, first_mean: float, second_mean: float, first_n: int, second_n: int, alpha: float = ALPHA):
    a = bool(n > 0 and mean_net > 0)
    b = bool(boot_p < alpha)
    d = bool(first_n > 0 and second_n > 0 and first_mean > 0 and second_mean > 0)
    e = bool(n >= MIN_TRADES)
    checks = {"a_mean_net_positive": a, "b_boot_p": b, "d_both_halves_positive": d, "e_min_60_trades": e}
    if a and b and d and e:
        return "SURVIVES", checks
    if a and b:
        return "INCONCLUSIVE", checks
    return "REJECT", checks


def summarise_trial(rows: list, skipped: list, n_expiries: int) -> dict:
    n = len(rows)
    out = {"n": n, "skipped": len(skipped), "n_expiries": n_expiries}
    if n == 0:
        out.update(verdict="REJECT", checks={}, boot_p=1.0)
        return out
    dates = [r["expiry"] for r in rows]
    for s in SLIPS:
        x = np.array([r[f"net_{s:.2f}"] for r in rows])
        out[f"mean_net_{s:.2f}"] = float(x.mean())
    net = np.array([r[f"net_{DECISION_SLIP:.2f}"] for r in rows])
    gross = np.array([r["gross_mid_rs"] for r in rows])
    out["mean_gross_mid"] = float(gross.mean())
    out["mean_fees_0.20"] = float(np.mean([r["fees_0.20"] for r in rows]))
    out["boot_p"] = fi.bootstrap_p(net)
    out["boot_p_by_slip"] = {f"{s:.2f}": fi.bootstrap_p(np.array([r[f"net_{s:.2f}"] for r in rows])) for s in SLIPS}
    out["boot_p_gross_mid"] = fi.bootstrap_p(gross)
    out.update(halves_means(dates, net))
    out["win_rate"] = float((net > 0).mean())
    out["worst_trade"] = float(net.min())
    out["best_trade"] = float(net.max())
    out["max_drawdown"] = float(max_drawdown(net))
    out["total_net"] = float(net.sum())
    out["verdict"], out["checks"] = verdict(out["mean_net_0.20"], out["boot_p"], n, out["first_mean"], out["second_mean"], out["first_n"], out["second_n"])
    out["calibration"] = calibration(rows)
    return out


def calibration(rows: list) -> dict:
    """Straddle price at 15:00 divided by the model Asian straddle value (literal 0.58 x sigma x sqrt(T)); also against the sqrt(2/pi) version."""
    px = np.array([r["straddle_px"] for r in rows])
    m1 = np.array([model_asian_straddle(r["sigma_pts"]) for r in rows])
    m2 = np.array([model_asian_straddle(r["sigma_pts"], True) for r in rows])
    ok = ~np.isnan(m1)
    return {"n": int(ok.sum()), "mean_straddle_px": float(px[ok].mean()), "mean_model_literal": float(m1[ok].mean()),
            "ratio_literal": float(px[ok].mean() / m1[ok].mean()), "mean_of_daily_ratios_literal": float(np.mean(px[ok] / m1[ok])),
            "median_daily_ratio_literal": float(np.median(px[ok] / m1[ok])),
            "ratio_with_sqrt2pi": float(px[ok].mean() / m2[ok].mean())}


# ------------------------------------------------------------------------------------------------ T3
def scan_strikes(k0: int) -> list:
    return [k0 + i * STEP for i in range(-SCAN // STEP, SCAN // STEP + 1)]


def last_oi(leg: pd.DataFrame | None, day: date):
    """OI of the last candle labelled at or before 14:50 on `day` that has an OI value, else None."""
    if leg is None:
        return None
    cut = datetime.combine(day, T_OI)
    d = leg[(leg.index.date == day) & (leg.index <= cut)]
    d = d[d["oi"].notna()] if "oi" in d.columns else d.iloc[0:0]
    return float(d["oi"].iloc[-1]) if len(d) else None


def pin_day(ex: date, s0: float, settle: float):
    """Per-day pin data, or (None, reason). Strikes count only when BOTH the call and the put have an OI value at or before 14:50."""
    k0 = round_strike(s0)
    pairs = {}
    for k in scan_strikes(k0):
        ce, pe = last_oi(load_leg(ex, k, "CE"), ex), last_oi(load_leg(ex, k, "PE"), ex)
        if ce is not None and pe is not None:
            pairs[k] = ce + pe
    if len(pairs) < 3:
        return None, "fewer_than_3_complete_strike_pairs"
    ks = sorted(pairs)
    k_max = min(k for k in ks if pairs[k] == max(pairs.values()))
    dist = np.array([abs(settle - k) for k in ks], float)
    return {"expiry": ex, "K0": k0, "A": settle, "strikes": ks, "K_max_oi": k_max, "dist_max": abs(settle - k_max), "dists": dist,
            "n_strikes": len(ks), "dist_spot_strike": abs(settle - k0), "max_oi": pairs[k_max],
            "tie": sum(1 for k in ks if pairs[k] == pairs[k_max]) > 1}, None


def pin_p_value(days: list, n_draw: int = N_DRAW, seed: int = SEED) -> dict:
    """One-sided p that the max-OI strike is closer to A than a uniformly random strike (statistic: mean over days of |A - K|)."""
    if not days:
        return {"n": 0, "p": 1.0}
    rng = np.random.default_rng(seed)
    obs = float(np.mean([d["dist_max"] for d in days]))
    null_sum = np.zeros(n_draw)
    for d in days:
        null_sum += d["dists"][rng.integers(0, len(d["dists"]), size=n_draw)]
    null = null_sum / len(days)
    return {"n": len(days), "obs_mean_dist": obs, "null_mean_dist": float(null.mean()), "null_q05": float(np.quantile(null, 0.05)),
            "expected_random_dist": float(np.mean([d["dists"].mean() for d in days])),
            "p": float((1 + np.sum(null <= obs + 1e-12)) / (n_draw + 1))}


def run_pin_test(bars, closes, expiries) -> dict:
    days, skipped = [], []
    for ex in expiries:
        f = day_frame(bars, ex)
        pair = s0_s1(f)
        if pair is None:
            skipped.append((ex, "no_1500_or_1525_bar"))
            continue
        if ex not in closes:
            skipped.append((ex, "no_daily_close"))
            continue
        d, why = pin_day(ex, pair[0], closes[ex])
        if d is None:
            skipped.append((ex, why))
        else:
            days.append(d)
    res = pin_p_value(days)
    res["days"], res["skipped"] = days, skipped
    if days:
        res["mean_dist_spot_strike"] = float(np.mean([d["dist_spot_strike"] for d in days]))
        res["share_max_oi_is_spot_strike"] = float(np.mean([d["K_max_oi"] == d["K0"] for d in days]))
        res["mean_abs_maxoi_minus_spotstrike"] = float(np.mean([abs(d["K_max_oi"] - d["K0"]) for d in days]))
        res["ties"] = int(sum(d["tie"] for d in days))
        res["mean_strikes"] = float(np.mean([d["n_strikes"] for d in days]))
        res["share_exact_pin"] = float(np.mean([d["dist_max"] <= 25 for d in days]))
    res["alpha"], res["pass"] = ALPHA, bool(res["p"] < ALPHA)
    return res
