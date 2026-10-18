"""Weekly NIFTY iron condor, SELLING premium, on REAL expired-option candles (study SELL1; rules in research/RESULTS.md).

Structure (1 lot = 75 units): sell call at spot*1.012 (rounded UP to 50) and put at spot*0.988 (rounded DOWN to 50),
buy wings 150 points beyond each. Entry: first 5-minute bar at/after 09:30 on the trading day nearest on-or-before
(expiry - 7 calendar days). V1 holds to expiry (intrinsic value of the official daily close); V2 adds a stop at a
mark-to-market loss of 2x the net credit, exiting at the next bar's open. Paper research only: no order code here.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scalp" / "options"))  # costs_opt only; NOT research/ (its evaluate.py would shadow ours)
from costs_opt import OptionCostModel  # noqa: E402  (existing, frozen cost model)

DATA = HERE.parent / "data"
OPT_DIR = DATA / "expired_options" / "NIFTY"
LOT = 75
STEP = 50
WING = 150
CALL_PCT, PUT_PCT = 1.012, 0.988
ENTRY_TIME = time(9, 30)
STOP_MULT = 2.0
SETTLE_STT = 0.0015  # on intrinsic value of an in-the-money leg that is cash-settled (0.15% from 1 Apr 2026)
DEV_CUTOFF = date(2026, 4, 16)
FIRST_EXPIRY = date(2024, 10, 3)
LEGS = ("sc", "lc", "sp", "lp")  # short call, long call, short put, long put


def short_strikes(spot: float) -> tuple[int, int]:
    """(short call, short put): call rounded UP and put rounded DOWN to a multiple of 50."""
    call = math.ceil(round(spot * CALL_PCT / STEP, 9)) * STEP
    put = math.floor(round(spot * PUT_PCT / STEP, 9)) * STEP
    return call, put


def leg_strikes(spot: float) -> dict[str, tuple[int, str]]:
    sc, sp = short_strikes(spot)
    return {"sc": (sc, "CE"), "lc": (sc + WING, "CE"), "sp": (sp, "PE"), "lp": (sp - WING, "PE")}


def intrinsic(kind: str, strike: float, settle: float) -> float:
    return max(settle - strike, 0.0) if kind == "CE" else max(strike - settle, 0.0)


def condor_settle_pnl_points(st: dict[str, tuple[int, str]], credit: float, settle: float) -> float:
    """P&L per unit, in points, of a condor held to expiry (credit is the net credit received at entry)."""
    v = {n: intrinsic(k, s, settle) for n, (s, k) in st.items()}
    owed = v["sc"] - v["lc"] + v["sp"] - v["lp"]
    return credit - owed


def settlement_stt(st: dict[str, tuple[int, str]], settle: float, qty: int = LOT, rate: float | None = None) -> float:
    """Settlement STT on every in-the-money leg (long and short: the conservative assumption) = rate x intrinsic x qty."""
    rate = SETTLE_STT if rate is None else rate
    return sum(rate * intrinsic(k, s, settle) * qty for s, k in st.values())


def entry_day(expiry: date, trading_days: list[date]) -> date | None:
    target = expiry - timedelta(days=7)
    c = [d for d in trading_days if d <= target]
    return max(c) if c else None


def entry_bar(bars: pd.DataFrame, day: date, shift: int = 0) -> int | None:
    """Row index (in bars) of the first 5-minute bar of `day` at or after 09:30, plus `shift` bars (diagnostic only)."""
    idx = bars.index[(bars["date"].dt.date == day) & (bars["date"].dt.time >= ENTRY_TIME)]
    if len(idx) == 0:
        return None
    i = idx[0] + shift
    return int(i) if 0 <= i < len(bars) else None


def load_leg(expiry: date, strike: int, kind: str) -> pd.DataFrame | None:
    f = OPT_DIR / f"{expiry.isoformat()}_{strike}{kind}.csv"
    if not f.exists():
        return None
    df = pd.read_csv(f, parse_dates=["date"]).sort_values("date").drop_duplicates("date")
    return df.set_index("date")


@dataclass
class Week:
    expiry: date
    skipped: str | None = None
    entry_ts: datetime | None = None
    spot: float = float("nan")
    strikes: dict = field(default_factory=dict)
    credit: float = float("nan")  # net credit per unit, after slippage
    settle: float = float("nan")
    stopped: bool = False
    stop_ts: datetime | None = None
    gross_pts: float = float("nan")  # per unit, before fees
    costs_rs: float = float("nan")
    net_rs: float = float("nan")
    breach: bool = False


def simulate_week(expiry: date, legs: dict[str, pd.DataFrame | None], bars: pd.DataFrame, settle_close: float | None,
                  e_idx: int | None, variant: str, cm: OptionCostModel, spot_shift: int = 0, strikes: dict | None = None) -> Week:
    """One condor. `bars` = NIFTY 5-minute bars (dev); `e_idx` = row of the entry bar; `settle_close` = official close on expiry day.
    Uses only candles at or before the decision time; the stop exits at the NEXT bar's open. `spot_shift` is a diagnostic for the
    lookahead check (spot = close of the bar `spot_shift` bars before the entry bar, e.g. -1 = previous bar)."""
    w = Week(expiry)
    if e_idx is None:
        w.skipped = "no_entry_bar"
        return w
    ets = bars.loc[e_idx, "date"]
    w.entry_ts = ets.to_pydatetime()
    w.spot = float(bars.loc[e_idx + spot_shift, "close"])
    st = strikes or leg_strikes(w.spot)
    w.strikes = st
    if settle_close is None:
        w.skipped = "no_settlement_close"
        return w
    if any(legs.get(n) is None for n in LEGS):
        w.skipped = "missing_option_file"
        return w
    if any(ets not in legs[n].index for n in LEGS):
        w.skipped = "no_candle_at_entry"
        return w
    slip, q = cm.slippage_rs, LOT
    fills = {n: max(legs[n].loc[ets, "open"] + (slip if n in ("lc", "lp") else -slip), 0.0) for n in LEGS}
    w.credit = fills["sc"] + fills["sp"] - fills["lc"] - fills["lp"]
    if w.credit <= 0:
        w.skipped = "nonpositive_credit"
        return w
    costs = sum(cm.side(fills[n], q, is_buy=n in ("lc", "lp")) for n in LEGS)
    w.settle = float(settle_close)
    w.breach = w.settle > st["sc"][0] or w.settle < st["sp"][0]
    if variant == "V2":
        grid = bars.loc[e_idx:, "date"]
        grid = grid[grid.dt.date <= expiry].reset_index(drop=True)
        closes = pd.DataFrame({n: legs[n]["close"].reindex(grid, method="ffill").to_numpy() for n in LEGS})
        mark_cost = closes["sc"] + closes["sp"] - closes["lc"] - closes["lp"]
        hit = (mark_cost - w.credit) >= STOP_MULT * w.credit
        if hit.any():
            i = int(hit.idxmax())
            w.stopped, w.stop_ts = True, grid[i].to_pydatetime()
            exit_px = {}
            for n in LEGS:
                if i + 1 < len(grid) and grid[i + 1] in legs[n].index:
                    px = float(legs[n].loc[grid[i + 1], "open"])
                else:
                    px = float(closes.loc[i, n])  # last known close
                exit_px[n] = max(px + slip, 0.0) if n in ("sc", "sp") else max(px - slip, 0.0)
            exit_cost = exit_px["sc"] + exit_px["sp"] - exit_px["lc"] - exit_px["lp"]
            w.gross_pts = w.credit - exit_cost
            costs += sum(cm.side(exit_px[n], q, is_buy=n in ("sc", "sp")) for n in LEGS)
    if not w.stopped:
        w.gross_pts = condor_settle_pnl_points(st, w.credit, w.settle)
        costs += settlement_stt(st, w.settle, q)
    w.costs_rs = costs
    w.net_rs = w.gross_pts * q - costs
    return w


def max_drawdown(x) -> float:
    """Largest peak-to-trough fall of cumulative weekly net P&L, starting equity 0 (<= 0)."""
    c = [0.0]
    for v in x:
        c.append(c[-1] + float(v))
    peak, dd = 0.0, 0.0
    for v in c:
        peak = max(peak, v)
        dd = min(dd, v - peak)
    return dd


def load_index():
    bars = pd.read_csv(DATA / "nifty_5minute_dev.csv", parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    daily = pd.read_csv(DATA / "nifty_day_dev.csv", parse_dates=["date"])
    closes = {d.date(): float(c) for d, c in zip(daily["date"], daily["close"])}
    ex = pd.read_csv(DATA / "nifty_expiries.csv")["expiry"].tolist()
    expiries = [date.fromisoformat(x) for x in ex if FIRST_EXPIRY <= date.fromisoformat(x) <= DEV_CUTOFF]
    return bars, closes, expiries


def run_all(variant: str, slippage: float, shift: int = 0, spot_shift: int = 0, cm_kwargs: dict | None = None):
    bars, closes, expiries = load_index()
    days = sorted(set(bars["date"].dt.date))
    cm = OptionCostModel(slippage_rs=slippage, **(cm_kwargs or {}))
    weeks = []
    for ex in expiries:
        d = entry_day(ex, days)
        e_idx = entry_bar(bars, d, shift) if d else None
        if e_idx is not None:
            st = leg_strikes(float(bars.loc[e_idx + spot_shift, "close"]))
            legs = {n: load_leg(ex, s, k) for n, (s, k) in st.items()}
        else:
            legs = {}
        weeks.append(simulate_week(ex, legs, bars, closes.get(ex), e_idx, variant, cm, spot_shift))
    return weeks
