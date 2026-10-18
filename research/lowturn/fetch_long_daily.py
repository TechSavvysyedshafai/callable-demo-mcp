"""Download daily NIFTY 50 bars (2000-01-03 to today) from Upstox and split dev / hidden holdout.

Run from research/:  python lowturn/fetch_long_daily.py
Token comes from the UPSTOX_ANALYTICS_TOKEN environment variable (never printed or written).
Saves the dev part to research/data/nifty_day_long_dev.csv; the newest 6 months go to the hidden holdout
directory (outside the repo) and are NOT read by research code.
NIFTY 50 here is the PRICE index: dividends (about 1.2-1.5%/yr) are not included.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent / "upstox")]

import kite_data as kd  # noqa: E402
import upstox_api as u  # noqa: E402

START = date(2000, 1, 3)


def main() -> None:
    df = u.historical(u.NIFTY, "days", 1, START, date.today())
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df["date"] = df["date"].dt.normalize()
    df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    dev, hold = kd.split(df, holdout_months=6)
    kd.DEV_DIR.mkdir(exist_ok=True)
    kd.HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)
    dev_p = kd.DEV_DIR / "nifty_day_long_dev.csv"
    hold_p = kd.HOLDOUT_DIR / "nifty_day_long_holdout.csv"
    dev.to_csv(dev_p, index=False)
    hold.to_csv(hold_p, index=False)
    print(f"downloaded {len(df)} bars {df['date'].min().date()} .. {df['date'].max().date()}")
    print(f"dev: {len(dev)} bars -> {dev_p} ({dev['date'].min().date()} .. {dev['date'].max().date()})")
    print(f"holdout: {len(hold)} bars written outside the repo (not read)")


if __name__ == "__main__":
    main()
