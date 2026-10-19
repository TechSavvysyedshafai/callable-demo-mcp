"""Download GOLDBEES and SILVERBEES daily candles (NSE_EQ) from Upstox into research/data (git-ignored dev CSVs).
Capped at the dev cutoff 2026-04-16: the request end date is the cutoff and rows after it are dropped again before saving.
Token: read from the UPSTOX_ANALYTICS_TOKEN environment variable by upstox_api.py; never printed or saved.
  python research/goldsilver/gs_fetch.py"""

import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
sys.path.insert(0, str(RESEARCH / "upstox"))
import upstox_api as u  # noqa: E402

CUTOFF = date(2026, 4, 16)
START = date(2015, 1, 1)  # far before either ETF listed; SILVERBEES' real first date is read from the data
DATA = RESEARCH / "data"
# Instrument keys found with the Upstox search API (/v2/instruments/search) on 2026-10-19; no secrets.
KEYS = {"GOLDBEES": "NSE_EQ|INF204KB17I5", "SILVERBEES": "NSE_EQ|INF204KC1402"}


def fetch(name: str):
    df = u.historical(KEYS[name], "days", 1, START, CUTOFF)
    df["date"] = df["date"].dt.normalize()
    df = df[df["date"] <= str(CUTOFF)]
    return df[["date", "open", "high", "low", "close", "volume"]].reset_index(drop=True)


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    for n in KEYS:
        d = fetch(n)
        p = DATA / f"{n.lower()}_day_dev.csv"
        d.to_csv(p, index=False)
        print(f"{n}: {len(d)} rows {d['date'].min().date()} -> {d['date'].max().date()} -> {p.name}")
