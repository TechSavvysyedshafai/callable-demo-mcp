"""Implied volatility inversion and Black-Scholes delta for the delta-neutral study.
Uses the repo's bs.py (read-only). Rate 6.5%; time runs to 15:30 IST on the expiry date (ACT/365). Model numbers are used ONLY to
pick strikes (25-delta); every P&L number comes from real option candles."""

from __future__ import annotations

import sys
from datetime import date, datetime, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scalp" / "options"))
import bs  # noqa: E402

RATE = 0.065
EXPIRY_CLOSE = time(15, 30)


def years_to_expiry(expiry: date, ts: datetime) -> float:
    """Years from ts to 15:30 IST on expiry day (floored at one minute so the formula never divides by zero)."""
    secs = (datetime.combine(expiry, EXPIRY_CLOSE) - ts).total_seconds()
    return max(secs, 60.0) / (365.0 * 86400.0)


def implied_vol(price: float, S: float, K: float, T: float, is_call: bool, r: float = RATE) -> float | None:
    """Invert Black-Scholes by bisection. None if the price is outside the no-arbitrage band (then IV is undefined)."""
    lo_px, hi_px = bs.price(S, K, T, 1e-6, is_call, r), bs.price(S, K, T, 5.0, is_call, r)
    if not (lo_px < price < hi_px):
        return None
    lo, hi = 1e-6, 5.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if bs.price(S, K, T, mid, is_call, r) < price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def delta_from_price(price: float, S: float, K: float, T: float, is_call: bool, r: float = RATE) -> float | None:
    """Delta using the strike's OWN implied vol (inverted from `price`). None if IV is undefined."""
    iv = implied_vol(price, S, K, T, is_call, r)
    return None if iv is None else bs.delta(S, K, T, iv, is_call, r)
