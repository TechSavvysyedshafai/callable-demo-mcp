"""Swing-range detector (interpretation of rule 1, fixed before any backtest).
15-minute fractal swings from the previous 3 sessions: a bar high that is strictly above the highs of the 3 bars on each side is a swing high;
a bar low strictly below the lows of the 3 bars on each side is a swing low. Resistance = nearest swing high ABOVE the spot,
support = nearest swing low BELOW the spot; both are required and the zone width must be 0.4%-1.5% of spot, else no trade that day.
Only sessions BEFORE the trading day are used (no lookahead)."""

from __future__ import annotations

import numpy as np
import pandas as pd

K_BARS = 3
MIN_WIDTH, MAX_WIDTH = 0.004, 0.015
N_SESSIONS = 3


def resample_15m(df5: pd.DataFrame) -> pd.DataFrame:
    """5-minute bars (date,open,high,low,close) -> 15-minute bars anchored at 09:15 (bar start labels), per calendar day."""
    d = df5.copy()
    d["b"] = d["date"].dt.floor("15min")
    g = d.groupby("b", sort=True)
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last()})
    out.index.name = "date"
    return out.reset_index()


def fractal_swings(high: np.ndarray, low: np.ndarray, k: int = K_BARS) -> tuple[list[float], list[float]]:
    """Values of swing highs and swing lows (strict extreme within k bars each side; the last k bars cannot be confirmed)."""
    h, l = np.asarray(high, float), np.asarray(low, float)
    highs, lows = [], []
    for i in range(k, len(h) - k):
        nb_h = np.r_[h[i - k:i], h[i + 1:i + k + 1]]
        nb_l = np.r_[l[i - k:i], l[i + 1:i + k + 1]]
        if h[i] > nb_h.max():
            highs.append(float(h[i]))
        if l[i] < nb_l.min():
            lows.append(float(l[i]))
    return highs, lows


def swing_range(prev15: pd.DataFrame, spot: float) -> tuple[float, float] | None:
    """(support, resistance) or None. prev15 = 15-minute bars of the previous sessions (already restricted to before today)."""
    if len(prev15) < 2 * K_BARS + 1:
        return None
    highs, lows = fractal_swings(prev15["high"].to_numpy(), prev15["low"].to_numpy())
    above = [x for x in highs if x > spot]
    below = [x for x in lows if x < spot]
    if not above or not below:
        return None
    R, S = min(above), max(below)
    w = (R - S) / spot
    return (S, R) if MIN_WIDTH <= w <= MAX_WIDTH else None


def previous_sessions(df15: pd.DataFrame, day, n: int = N_SESSIONS) -> pd.DataFrame:
    """The 15-minute bars of the n sessions strictly before `day`."""
    days = df15["date"].dt.normalize()
    prior = sorted(set(days[days < pd.Timestamp(day)]))[-n:]
    return df15[days.isin(prior)].reset_index(drop=True)
