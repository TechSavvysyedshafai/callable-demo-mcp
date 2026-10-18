"""Download NIFTY 50 intraday bars + India VIX from Upstox into the same files the research harness already reads.

  python fetch_upstox.py                # 3 years of 5-minute bars (Upstox minute data starts Jan 2022)
The newest --holdout-months are saved OUTSIDE the repo (~/.nifty_holdout) as the hidden final test set.
"""

import argparse
import sys
from datetime import date, time, timedelta
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import kite_data as kd  # reuses the dev / hidden-holdout split and file layout
import upstox_api as u

if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--years", type=float, default=3)
    a.add_argument("--minutes", type=int, default=5, choices=[1, 3, 5, 15])
    a.add_argument("--holdout-months", type=int, default=6)
    a = a.parse_args()
    end = date.today()
    start = max(end - timedelta(days=int(365 * a.years)), date(2022, 1, 3))  # minute data starts Jan 2022
    print(f"Downloading NIFTY {a.minutes}-minute bars {start} -> {end} (about {(end - start).days // 28 + 1} requests)...")
    df = u.historical(u.NIFTY, "minutes", a.minutes, start, end)
    df = df[df["date"].dt.time >= time(9, 15)].reset_index(drop=True)
    name = "minute" if a.minutes == 1 else f"{a.minutes}minute"
    dev_p, hold_p = kd.write_split(df[["date", "open", "high", "low", "close", "volume"]], name, a.holdout_months)
    print(f"{len(df)} bars -> dev: {dev_p}\n   holdout (hidden, do not open): {hold_p}")
    v = u.historical(u.INDIA_VIX, "days", 1, start, end)
    v["date"] = v["date"].dt.normalize()
    kd.DEV_DIR.mkdir(exist_ok=True)
    v[["date", "close"]].to_csv(kd.DEV_DIR / "india_vix_day.csv", index=False)
    print(f"India VIX: {len(v)} days saved")
    try:  # real expiry dates (needs Plus): the model-based option backtest must not guess expiry weekdays
        ex = sorted(u.get("/v2/expired-instruments/expiries", {"instrument_key": u.NIFTY})["data"])
        import pandas as pd
        pd.DataFrame({"expiry": ex}).to_csv(kd.DEV_DIR / "nifty_expiries.csv", index=False)
        print(f"NIFTY expiries: {len(ex)} ({ex[0]} to {ex[-1]}) saved")
    except u.UpstoxError as e:
        print("Expiry calendar skipped:", "needs Upstox Plus" if e.needs_plus else e)
