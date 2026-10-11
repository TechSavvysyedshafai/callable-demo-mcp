"""Download India VIX daily closes (IV input for the model-based backtest) and, for non-NIFTY underlyings,
the index bars. Needs KITE_API_KEY / KITE_ACCESS_TOKEN. Index bars for NIFTY come from ../../fetch_data.py."""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
for p in (HERE, HERE.parent, HERE.parent.parent):
    sys.path.insert(0, str(p))
import kite_data as kd
from contracts import UNDERLYINGS

INDIA_VIX_TOKEN = 264969  # VERIFY via the NSE instruments dump (tradingsymbol "INDIA VIX")

if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--years", type=float, default=3)
    a.add_argument("--underlying", default="NIFTY", choices=list(UNDERLYINGS))
    a.add_argument("--interval", default="5minute")
    a.add_argument("--holdout-months", type=int, default=6)
    a = a.parse_args()
    end, start = date.today(), date.today() - timedelta(days=int(365 * a.years))
    kd.DEV_DIR.mkdir(exist_ok=True)
    v = kd.fetch_candles(INDIA_VIX_TOKEN, "day", start, end)
    v["date"] = v["date"].dt.normalize()
    v.to_csv(kd.DEV_DIR / "india_vix_day.csv", index=False)
    print(f"VIX: {len(v)} days")
    if a.underlying != "NIFTY":
        df = kd.fetch_candles(UNDERLYINGS[a.underlying]["token"], a.interval, start, end)
        print(kd.write_split(df, a.interval, a.holdout_months))
