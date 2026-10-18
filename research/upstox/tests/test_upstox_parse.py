"""Offline tests: request building, chunking, candle parsing and strike picking (no network, no token)."""

import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent.parent
sys.path.insert(0, str(HERE))
import download_expired_options as d
import upstox_api as u

calls = []


def fake_get(path, params=None, retries=4):
    calls.append(path)
    # newest-first, as Upstox returns; second row duplicated across chunks to test de-duplication
    return {"data": {"candles": [["2025-01-02T09:20:00+05:30", 2, 3, 1, 2.5, 100, 0],
                                 ["2025-01-02T09:15:00+05:30", 1, 2, 0.5, 1.5, 50, 0]]}}


u.get = fake_get
df = u.historical(u.NIFTY, "minutes", 5, date(2025, 1, 1), date(2025, 3, 1))
assert len(calls) == 3, calls  # 60 days in 28-day chunks
assert "NSE_INDEX%7CNifty%2050/minutes/5/" in calls[0]  # key is URL-encoded, 'to' date before 'from' date
assert calls[0].split("/")[-2:] == ["2025-01-28", "2025-01-01"]
assert list(df["date"].dt.strftime("%H:%M")) == ["09:15", "09:20"]  # sorted ascending, IST, duplicates removed
assert df["oi"].iloc[0] == 0 and df["volume"].iloc[1] == 100
e = u.expired_candles("NSE_FO|73507|24-04-2025", "5minute", date(2025, 4, 17), date(2025, 4, 24))
assert "NSE_FO%7C73507%7C24-04-2025/5minute/2025-04-24/2025-04-17" in calls[-1]
cs = [{"strike_price": k, "instrument_type": t} for k in range(24000, 25001, 50) for t in ("CE", "PE")]
picked = d.pick_strikes(cs, 24520, 50, 5)
assert {float(c["strike_price"]) for c in picked} == {24250 + 50 * i for i in range(11)}, picked
assert u.UpstoxError(403, '{"errorCode":"UDAPI1149"}').needs_plus
print("upstox parse ok")
