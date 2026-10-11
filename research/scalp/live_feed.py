"""LIVE paper trading: Kite WebSocket ticks for the nearest NIFTY future -> N-minute bars -> PaperTrader.
UNTESTED against the real feed (needs a Kite Connect subscription + today's token, market hours).
Needs: pip install kiteconnect. Env: KITE_API_KEY, KITE_ACCESS_TOKEN.
"""

import argparse
import csv
import io
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import pandas as pd
from paper import Fleet


def nearest_nifty_future() -> tuple[int, str]:
    key, tok = os.environ["KITE_API_KEY"], os.environ["KITE_ACCESS_TOKEN"]
    req = urllib.request.Request("https://api.kite.trade/instruments/NFO",
                                 headers={"X-Kite-Version": "3", "Authorization": f"token {key}:{tok}"})
    rows = list(csv.DictReader(io.StringIO(urllib.request.urlopen(req, timeout=30).read().decode())))
    futs = [r for r in rows if r["name"] == "NIFTY" and r["instrument_type"] == "FUT"]
    f = min(futs, key=lambda r: r["expiry"])
    return int(f["instrument_token"]), f["tradingsymbol"]


class BarBuilder:
    def __init__(self, minutes, on_bar):
        self.m, self.on_bar, self.cur = minutes, on_bar, None

    def tick(self, ts: datetime, px: float):
        bucket = pd.Timestamp(ts).floor(f"{self.m}min").to_pydatetime().replace(tzinfo=None)
        if self.cur and self.cur["t"] != bucket:
            c = self.cur
            self.on_bar(pd.Timestamp(c["t"]), c["o"], c["h"], c["l"], c["c"])
            self.cur = None
        if self.cur is None:
            self.cur = {"t": bucket, "o": px, "h": px, "l": px, "c": px}
        else:
            self.cur["h"], self.cur["l"], self.cur["c"] = max(self.cur["h"], px), min(self.cur["l"], px), px


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--minutes", type=int, default=5)
    a = a.parse_args()
    from kiteconnect import KiteTicker

    token, symbol = nearest_nifty_future()
    print(f"paper trading {symbol} on {a.minutes}-minute bars; create ./KILL to halt")
    trader = Fleet()
    bars = BarBuilder(a.minutes, trader.on_bar)
    kws = KiteTicker(os.environ["KITE_API_KEY"], os.environ["KITE_ACCESS_TOKEN"])
    kws.on_connect = lambda ws, _: (ws.subscribe([token]), ws.set_mode(ws.MODE_LTP, [token]))
    kws.on_ticks = lambda ws, ticks: [bars.tick(t.get("exchange_timestamp") or datetime.now(), t["last_price"]) for t in ticks]
    kws.on_close = lambda ws, code, reason: trader.end_session()
    kws.connect()
