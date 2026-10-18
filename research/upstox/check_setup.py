"""Run this FIRST. It tests your Upstox token step by step and tells you what to do next. Prints no secrets."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import upstox_api as u

ok = True


def step(name, fn):
    global ok
    try:
        print(f"[ OK ] {name}: {fn()}")
    except u.UpstoxError as e:
        ok = False
        if e.needs_plus:
            print(f"[PLUS] {name}: needs the Upstox Plus plan (error UDAPI1149). Free data still works; see README step 6.")
        elif e.code == 401:
            print(f"[FAIL] {name}: token rejected (401). Regenerate the Analytics Token and set it again.")
        else:
            print(f"[FAIL] {name}: {e}")


def live_price():
    d = u.get("/v2/market-quote/ltp", {"instrument_key": u.NIFTY})["data"]
    return f"got a live quote ({len(d)} item) - market data works"


def history():
    today = date.today()
    df = u.historical(u.NIFTY, "minutes", 5, today - timedelta(days=7), today)
    return f"{len(df)} five-minute NIFTY candles from the last week"


def vix():
    today = date.today()
    df = u.historical(u.INDIA_VIX, "days", 1, today - timedelta(days=30), today)
    return f"{len(df)} daily India VIX candles"


def expired():
    ex = u.get("/v2/expired-instruments/expiries", {"instrument_key": u.NIFTY})["data"]
    return f"{len(ex)} expired NIFTY expiries available, earliest {min(ex)}, latest {max(ex)}"


step("live price (NIFTY 50)", live_price)
step("intraday history", history)
step("India VIX history", vix)
step("expired option history (Plus feature)", expired)
print("\nAll core checks passed." if ok else "\nSome checks did not pass - read the lines above.")
