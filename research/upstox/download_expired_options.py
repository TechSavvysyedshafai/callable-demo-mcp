"""Save real expired-option candles (needs the Upstox Plus plan). UNTESTED against the live API.
For each recent expiry it downloads ATM +/- N strikes, calls and puts, as CSV (date,open,high,low,close,volume,oi).
Upstox's docs say about 6 months of expiries; a real account listed ~2 years (from Oct 2024). Run it regularly to grow your archive.

  python download_expired_options.py --underlying NIFTY --expiries 26 --strikes 5
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import kite_data as kd
import upstox_api as u

# key = Upstox underlying key; step = strike spacing; days = how long before expiry the contract trades
UNDERLYINGS = {
    "NIFTY": dict(key="NSE_INDEX|Nifty 50", step=50, days=9),
    "BANKNIFTY": dict(key="NSE_INDEX|Nifty Bank", step=100, days=35),  # monthly expiries only
}


def pick_strikes(contracts: list[dict], spot: float, step: int, n: int) -> list[dict]:
    atm = round(spot / step) * step
    lo, hi = atm - n * step, atm + n * step
    return [c for c in contracts if lo <= float(c["strike_price"]) <= hi]


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--underlying", default="NIFTY", choices=list(UNDERLYINGS))
    a.add_argument("--expiries", type=int, default=26)
    a.add_argument("--strikes", type=int, default=5)
    a.add_argument("--interval", default="5minute")
    a = a.parse_args()
    cfg = UNDERLYINGS[a.underlying]
    out = kd.DEV_DIR / "expired_options" / a.underlying
    out.mkdir(parents=True, exist_ok=True)
    try:
        expiries = sorted(u.get("/v2/expired-instruments/expiries", {"instrument_key": cfg["key"]})["data"])[-a.expiries:]
    except u.UpstoxError as e:
        raise SystemExit("This needs the Upstox Plus plan (UDAPI1149)." if e.needs_plus else str(e))
    first = date.fromisoformat(expiries[0]) - timedelta(days=cfg["days"] + 5)
    daily = u.historical(cfg["key"], "days", 1, first, date.today())
    closes = {d.date(): c for d, c in zip(daily["date"], daily["close"])}
    saved = 0
    for ex in expiries:
        exp = date.fromisoformat(ex)
        prev = max((d for d in closes if d < exp), default=None)
        if prev is None:
            continue
        contracts = u.get("/v2/expired-instruments/option/contract", {"instrument_key": cfg["key"], "expiry_date": ex})["data"]
        for c in pick_strikes(contracts, closes[prev], cfg["step"], a.strikes):
            f = out / f"{ex}_{int(float(c['strike_price']))}{c['instrument_type']}.csv"
            if f.exists():
                continue
            df = u.expired_candles(c["instrument_key"], a.interval, exp - timedelta(days=cfg["days"]), exp)
            if len(df):
                df.to_csv(f, index=False)
                saved += 1
        print(f"{ex}: done ({saved} files so far)")
    print(f"Saved {saved} contract files under {out}")
