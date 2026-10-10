"""Download NIFTY 50 candles from Kite and split into dev (repo) / holdout (outside repo)."""

import argparse
from datetime import date, timedelta

import kite_data as kd

p = argparse.ArgumentParser()
p.add_argument("--interval", default="day", choices=list(kd.MAX_SPAN_DAYS))
p.add_argument("--years", type=float, default=8)
p.add_argument("--holdout-months", type=int, default=6)
p.add_argument("--synthetic", action="store_true", help="offline dry run, no Kite needed")
a = p.parse_args()

if a.synthetic:
    df = kd.synthetic()
else:
    end = date.today()
    df = kd.fetch_candles(kd.NIFTY50_TOKEN, a.interval, end - timedelta(days=int(365 * a.years)), end)
dev_p, hold_p = kd.write_split(df, a.interval, a.holdout_months)
print(f"{len(df)} bars -> dev {dev_p} | holdout {hold_p} (outside the repo; do not open it)")
