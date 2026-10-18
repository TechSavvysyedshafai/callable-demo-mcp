"""Loads saved REAL expired-option candles (files like 2025-01-09_24500CE.csv: date,open,high,low,close,volume,oi)."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})_(\d+)(CE|PE)\.csv$")


class OptionBook:
    def __init__(self, folder: Path):
        self.t: dict[tuple, np.ndarray] = {}  # key -> sorted datetime64 array
        self.px: dict[tuple, np.ndarray] = {}  # key -> Nx4 array (open, high, low, close)
        self.vol: dict[tuple, np.ndarray] = {}
        self.strikes: dict[tuple, list[int]] = {}  # (expiry, type) -> sorted strikes
        for f in sorted(Path(folder).glob("*.csv")):
            m = _NAME.search(f.name)
            if not m:
                continue
            df = pd.read_csv(f, parse_dates=["date"]).sort_values("date")
            if df.empty:
                continue
            key = (date.fromisoformat(m.group(1)), int(m.group(2)), m.group(3))
            self.t[key] = df["date"].to_numpy("datetime64[ns]")
            self.px[key] = df[["open", "high", "low", "close"]].to_numpy(float)
            self.vol[key] = df["volume"].to_numpy(float)
            self.strikes.setdefault((key[0], key[2]), []).append(key[1])
        for v in self.strikes.values():
            v.sort()

    def __len__(self) -> int:
        return len(self.t)

    def pick(self, expiry: date, typ: str, spot: float, max_gap: float):
        """Key of the saved strike nearest to spot (within max_gap points), else None."""
        ks = self.strikes.get((expiry, typ))
        if not ks:
            return None
        best = min(ks, key=lambda k: abs(k - spot))
        return (expiry, best, typ) if abs(best - spot) <= max_gap else None

    def row(self, key, ts) -> np.ndarray | None:
        """(open, high, low, close) of the candle starting exactly at ts, or None if the option didn't trade then."""
        t = self.t[key]
        i = int(np.searchsorted(t, np.datetime64(ts, "ns")))
        return self.px[key][i] if i < len(t) and t[i] == np.datetime64(ts, "ns") else None

    def last_close(self, key, ts) -> float | None:
        t = self.t[key]
        i = int(np.searchsorted(t, np.datetime64(ts, "ns"), side="right")) - 1
        return float(self.px[key][i][3]) if i >= 0 else None
