"""Data access: Kite historical candles -> local CSV, plus a synthetic generator for dry runs.

Env: KITE_API_KEY, KITE_ACCESS_TOKEN (the access token expires daily).
The holdout slice is written OUTSIDE the repo (HOLDOUT_DIR) so the research agent,
which only works inside this directory, never sees it.
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

KITE = "https://api.kite.trade"
NIFTY50_TOKEN = 256265  # NSE:NIFTY 50
HERE = Path(__file__).parent
DEV_DIR = HERE / "data"
HOLDOUT_DIR = Path(os.environ.get("HOLDOUT_DIR", Path.home() / ".nifty_holdout"))
COLS = ["date", "open", "high", "low", "close", "volume"]

# Kite caps the date span per historical request.
MAX_SPAN_DAYS = {"day": 2000, "60minute": 400, "15minute": 200, "5minute": 100, "minute": 60}


def _get(path: str, params: dict) -> dict:
    key, token = os.environ.get("KITE_API_KEY"), os.environ.get("KITE_ACCESS_TOKEN")
    if not key or not token:
        raise SystemExit("Set KITE_API_KEY and KITE_ACCESS_TOKEN (or use --synthetic).")
    req = urllib.request.Request(
        f"{KITE}{path}?{urllib.parse.urlencode(params)}",
        headers={"X-Kite-Version": "3", "Authorization": f"token {key}:{token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("status") != "success":
        raise RuntimeError(body.get("message", body))
    return body["data"]


def fetch_candles(token: int, interval: str, start: date, end: date) -> pd.DataFrame:
    span = timedelta(days=MAX_SPAN_DAYS[interval] - 1)
    rows, cur = [], start
    while cur <= end:
        stop = min(cur + span, end)
        data = _get(
            f"/instruments/historical/{token}/{interval}",
            {"from": cur.isoformat(), "to": stop.isoformat()},
        )
        rows += data["candles"]
        cur = stop + timedelta(days=1)
        time.sleep(0.4)  # historical endpoint is limited to ~3 req/s
    df = pd.DataFrame(rows, columns=COLS)
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def synthetic(n: int = 2200, seed: int = 0, persistent_vol: bool = True) -> pd.DataFrame:
    """Fake index with AR(1) log-vol (range is forecastable) and unforecastable direction."""
    rng = np.random.default_rng(seed)
    phi = 0.97 if persistent_vol else 0.0
    logv, rows, price = np.log(0.01), [], 10000.0
    for d in pd.bdate_range("2015-01-01", periods=n):
        logv = phi * logv + (1 - phi) * np.log(0.01) + 0.15 * rng.standard_normal()
        steps = np.cumsum(np.exp(logv) / np.sqrt(25) * rng.standard_normal(25))
        path = price * np.exp(steps)
        rows.append([d, price, path.max(), path.min(), path[-1], int(1e6 * rng.random())])
        price = path[-1]
    return pd.DataFrame(rows, columns=COLS)


def split(df: pd.DataFrame, holdout_months: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    cut = df["date"].max() - pd.DateOffset(months=holdout_months)
    return df[df["date"] <= cut].reset_index(drop=True), df[df["date"] > cut].reset_index(drop=True)


def write_split(df: pd.DataFrame, interval: str, holdout_months: int) -> tuple[Path, Path]:
    dev, hold = split(df, holdout_months)
    DEV_DIR.mkdir(exist_ok=True)
    HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)
    dev_p, hold_p = DEV_DIR / f"nifty_{interval}_dev.csv", HOLDOUT_DIR / f"nifty_{interval}_holdout.csv"
    dev.to_csv(dev_p, index=False)
    hold.to_csv(hold_p, index=False)
    return dev_p, hold_p


def load_dev(interval: str = "day") -> pd.DataFrame:
    return pd.read_csv(DEV_DIR / f"nifty_{interval}_dev.csv", parse_dates=["date"])


def load_holdout(interval: str = "day") -> pd.DataFrame:
    """Only final_holdout.py may call this."""
    return pd.read_csv(HOLDOUT_DIR / f"nifty_{interval}_holdout.csv", parse_dates=["date"])
