"""DEV-ONLY download of NIFTY 5-minute bars, NIFTY daily bars, India VIX and NIFTY expiries.

Requests stop at DEV_CUT (the last day of the development period). Nothing after that date is requested from Upstox,
so the hidden holdout is never downloaded, never written and never read. Writes the dev files the loop reads:
research/data/nifty_5minute_dev.csv, nifty_day_dev.csv, india_vix_day.csv, nifty_expiries.csv

  python fetch_dev_only.py
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import upstox_api as u  # noqa: E402

DEV_CUT = date(2026, 4, 16)  # last day of the development period (same cut as the loop's dev files)
MINUTE_START = date(2022, 1, 3)  # Upstox minute history starts here
DEV_DIR = HERE.parent / "data"


def _dev_only(df: pd.DataFrame, cut: pd.Timestamp) -> pd.DataFrame:
    return df[df["date"] <= cut].reset_index(drop=True)


if __name__ == "__main__":
    DEV_DIR.mkdir(exist_ok=True)
    cut = pd.Timestamp(DEV_CUT) + pd.Timedelta(hours=23, minutes=59)
    m = u.historical(u.NIFTY, "minutes", 5, MINUTE_START, DEV_CUT)
    m = m[m["date"].dt.time >= pd.Timestamp("09:15").time()]
    m = _dev_only(m[["date", "open", "high", "low", "close", "volume"]], cut)
    m.to_csv(DEV_DIR / "nifty_5minute_dev.csv", index=False)
    print(f"5-minute dev bars: {len(m)} ({m['date'].min()} to {m['date'].max()})")

    d = u.historical(u.NIFTY, "days", 1, date(2016, 1, 1), DEV_CUT)
    d = _dev_only(d[["date", "open", "high", "low", "close", "volume"]], cut)
    d.to_csv(DEV_DIR / "nifty_day_dev.csv", index=False)
    print(f"daily dev bars: {len(d)} ({d['date'].min().date()} to {d['date'].max().date()})")

    v = u.historical(u.INDIA_VIX, "days", 1, date(2016, 1, 1), DEV_CUT)
    v["date"] = v["date"].dt.normalize()
    v = _dev_only(v[["date", "close"]], cut)
    v.to_csv(DEV_DIR / "india_vix_day.csv", index=False)
    print(f"India VIX dev days: {len(v)}")

    try:
        ex = u.get("/v2/expired-instruments/expiries", {"instrument_key": u.NIFTY})["data"]
        ex = sorted(x for x in ex if date.fromisoformat(x) <= DEV_CUT)
        pd.DataFrame({"expiry": ex}).to_csv(DEV_DIR / "nifty_expiries.csv", index=False)
        print(f"NIFTY expiries (dev): {len(ex)}")
    except u.UpstoxError as e:
        print("Expiry calendar skipped:", "needs Upstox Plus" if e.needs_plus else e)
