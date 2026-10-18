"""Independent re-computation of the daily range-forecast numbers. Deliberately does NOT import research/harness.py or candidate.py:
numpy + csv only, its own rolling windows and its own block bootstrap. If this agrees with research/evaluate.py, a bug in the harness
(off-by-one, leakage through its slicing) is very unlikely.

  python research/qa/repro_daily_mae.py
Reads research/data/nifty_day_dev.csv (dev only).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parent.parent / "data" / "nifty_day_dev.csv"
MIN_TRAIN = 250  # first forecast origin index (same rule the lab states: at least 250 days of history)
LAM, EW_WINDOW = 0.94, 120


def load(path: Path = DATA):
    dates, hi, lo = [], [], []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            dates.append(row["date"][:10])
            hi.append(float(row["high"]))
            lo.append(float(row["low"]))
    return np.array(dates), np.log(np.array(hi) / np.array(lo))


def rolling_mean(x: np.ndarray, w: int) -> np.ndarray:
    """m[i] = mean(x[i-w+1..i]) for i >= w-1 (NaN before)."""
    c = np.concatenate([[0.0], np.cumsum(x)])
    m = np.full(len(x), np.nan)
    m[w - 1:] = (c[w:] - c[:-w]) / w
    return m


def forecasts(r: np.ndarray) -> dict:
    """Forecast for the day AFTER each origin i, using r[:i+1] only. Returns arrays indexed by origin i = MIN_TRAIN .. n-2."""
    n = len(r)
    origins = np.arange(MIN_TRAIN, n - 1)
    m5, m22, m20 = rolling_mean(r, 5), rolling_mean(r, 22), rolling_mean(r, 20)
    w = LAM ** np.arange(EW_WINDOW)[::-1]  # oldest .. newest = lam^119 .. 1
    win = np.lib.stride_tricks.sliding_window_view(r, EW_WINDOW)  # win[j] = r[j..j+119]; ends at j+119
    ew = (win @ w) / w.sum()
    ew_at = np.full(n, np.nan)
    ew_at[EW_WINDOW - 1:] = ew
    return {
        "origins": origins,
        "y": r[origins + 1],
        "candidate": 0.4 * r[origins] + 0.3 * m5[origins] + 0.3 * m22[origins],
        "random_walk": r[origins],
        "mean20": m20[origins],
        "ewma94": ew_at[origins],
    }


def block_bootstrap_lower(d: np.ndarray, alpha: float, block: int = 5, reps: int = 20000, seed: int = 2024) -> float:
    rng = np.random.default_rng(seed)
    n = len(d)
    nb = -(-n // block)
    start = rng.integers(0, n - block + 1, size=(reps, nb))
    idx = (start[:, :, None] + np.arange(block)[None, None, :]).reshape(reps, nb * block)[:, :n]
    return float(np.quantile(d[idx].mean(axis=1), alpha))


def summarize(path: Path = DATA) -> dict:
    dates, r = load(path)
    f = forecasts(r)
    names = ["candidate", "random_walk", "mean20", "ewma94"]
    mae = {k: float(np.mean(np.abs(f["y"] - f[k]))) for k in names}
    best = min(["random_walk", "mean20", "ewma94"], key=lambda k: mae[k])
    d = np.abs(f["y"] - f[best]) - np.abs(f["y"] - f["candidate"])  # > 0: candidate closer
    return {
        "rows": len(r), "first_target_date": str(dates[f["origins"][0] + 1]), "last_target_date": str(dates[f["origins"][-1] + 1]),
        "n_origins": len(f["origins"]), "mae": mae, "best_baseline": best,
        "rel_improvement": float(d.mean() / np.mean(np.abs(f["y"] - f[best]))),
        "ci_lower_gain_alpha_0.05": block_bootstrap_lower(d, 0.05),
    }


if __name__ == "__main__":
    print(json.dumps(summarize(), indent=2))
