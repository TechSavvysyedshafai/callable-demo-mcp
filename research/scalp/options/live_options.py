"""LIVE option paper trading + quote recording for Kite. UNTESTED against the real feed (needs a Kite Connect
subscription, today's token, and market hours). Needs: pip install kiteconnect.

  python live_options.py --underlying NIFTY          # paper trade (fills at real bid/ask) AND record quotes
Quotes are saved to data/options_ticks/<date>.csv - Kite has no expired-contract history, so THIS is how you
build a real option dataset for honest backtests. Create scalp/KILL to halt. No real orders are ever placed.
"""

import argparse
import csv
import io
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
for p in (HERE, HERE.parent, HERE.parent.parent):
    sys.path.insert(0, str(p))
import strategy
from contracts import UNDERLYINGS
from engine import Risk
from opt_engine import OptParams
from quote_paper import QuotePaper, pick_contract
from live_feed import BarBuilder


def instruments(exch: str):
    key, tok = os.environ["KITE_API_KEY"], os.environ["KITE_ACCESS_TOKEN"]
    req = urllib.request.Request(f"https://api.kite.trade/instruments/{exch}",
                                 headers={"X-Kite-Version": "3", "Authorization": f"token {key}:{tok}"})
    return list(csv.DictReader(io.StringIO(urllib.request.urlopen(req, timeout=60).read().decode())))


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--underlying", default="NIFTY", choices=list(UNDERLYINGS))
    a.add_argument("--minutes", type=int, default=5)
    a.add_argument("--strikes", type=int, default=4, help="record this many strikes each side of ATM")
    a = a.parse_args()
    from kiteconnect import KiteTicker

    cfg, params = UNDERLYINGS[a.underlying], OptParams(**strategy.OPTIONS)
    rows = [r for r in instruments(cfg["exch"]) if r["name"] == a.underlying and r["instrument_type"] in ("CE", "PE")]
    outdir = HERE.parent.parent / "data" / "options_ticks"
    outdir.mkdir(parents=True, exist_ok=True)
    rec = (outdir / f"{datetime.now():%Y-%m-%d}_{a.underlying}.csv").open("a", newline="")
    wr = csv.writer(rec)
    kws = KiteTicker(os.environ["KITE_API_KEY"], os.environ["KITE_ACCESS_TOKEN"])
    subscribed = set()

    def resolve(d, spot, ts):
        return pick_contract(rows, a.underlying, spot, "CE" if d > 0 else "PE", ts.date(), params.min_dte_days)

    def subscribe(tok):
        if tok not in subscribed:
            subscribed.add(tok)
            kws.subscribe([tok]); kws.set_mode(kws.MODE_FULL, [tok])

    trader = QuotePaper(strategy.make(), params, a.underlying, resolve, subscribe,
                        risk=Risk(kill_file=str(HERE.parent / "KILL")),
                        log=HERE.parent / "state" / "logs" / f"options_{a.underlying}_trades.csv")
    bars = BarBuilder(a.minutes, trader.on_index_bar)

    def on_ticks(ws, ticks):
        for t in ticks:
            ts = t.get("exchange_timestamp") or datetime.now()
            if t["instrument_token"] == cfg["token"]:
                bars.tick(ts, t["last_price"])
                continue
            depth = t.get("depth") or {}
            bid = (depth.get("buy") or [{}])[0].get("price", 0.0)
            ask = (depth.get("sell") or [{}])[0].get("price", 0.0)
            wr.writerow([ts.isoformat(), t["instrument_token"], t["last_price"], bid, ask, t.get("volume_traded"), t.get("oi")])
            trader.on_quote(t["instrument_token"], ts, bid, ask)
        rec.flush()

    def on_connect(ws, _):
        ws.subscribe([cfg["token"]]); ws.set_mode(ws.MODE_LTP, [cfg["token"]])

    kws.on_connect, kws.on_ticks = on_connect, on_ticks
    print(f"paper trading {a.underlying} options (buy CE/PE at ask, sell at bid) and recording quotes; create ./KILL to halt")
    kws.connect()
