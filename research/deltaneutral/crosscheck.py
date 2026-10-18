"""Independent arithmetic check (adversarial-review item 9). Does NOT use backtest.py, option_book.py or costs_opt.py.
For every traded day in results/events_<V>_0.20.json it re-reads each fill's candle straight from the raw CSV, re-applies the slippage and the fee
formula written out by hand, and compares gross, costs and net with the harness. It checks bookkeeping and candle look-ups, not the strategy logic."""

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OPT = HERE.parent / "data" / "expired_options" / "NIFTY"
QTY, SLIP = 75, 0.20
_cache = {}


def candle_open(expiry, strike, typ, ts):
    f = OPT / f"{expiry}_{int(strike)}{typ}.csv"
    if f not in _cache:
        _cache[f] = pd.read_csv(f, parse_dates=["date"]).set_index("date")
    return float(_cache[f].loc[pd.Timestamp(ts), "open"])


def fee(price, is_buy):
    turn = price * QTY
    brok, exch, sebi = 20.0, 0.0003553 * turn, 0.000001 * turn
    gst = 0.18 * (brok + exch + sebi)
    return brok + exch + sebi + gst + (0.00003 * turn if is_buy else 0.0015 * turn)


def check(variant):
    days = json.loads((HERE / "results" / f"events_{variant}_0.20.json").read_text())
    worst = 0.0
    for d in days:
        ex, buys, sells = d["expiry"], [], []
        for e in d["events"]:
            t = e["fill_ts"]
            if e["kind"] == "enter":
                sells += [(ex, e["call"], "CE", t), (ex, e["put"], "PE", t)]
                if e["wing_call"] is not None:
                    buys += [(ex, e["wing_call"], "CE", t), (ex, e["wing_put"], "PE", t)]
            elif e["kind"] == "adjust":
                other = e["typ"]
                buys.append((ex, e["old_strike"], other, t))
                sells.append((ex, e["new_strike"], other, t))
            elif e["kind"] == "exit_leg":
                (sells if e["leg"].startswith("w") else buys).append((ex, e["strike"], e["typ"], t))
        sp = [max(candle_open(*k) - SLIP, 0.05) for k in sells]
        bp = [candle_open(*k) + SLIP for k in buys]
        gross = QTY * (sum(sp) - sum(bp))
        cost = sum(fee(p, False) for p in sp) + sum(fee(p, True) for p in bp)
        worst = max(worst, abs(gross - d["gross"]), abs(cost - d["cost"]), abs(gross - cost - d["net"]))
        assert len(sp) + len(bp) == d["orders"], (d["day"], len(sp) + len(bp), d["orders"])
    return len(days), worst


if __name__ == "__main__":
    for v in "ABC":
        n, w = check(v)
        print(f"variant {v}: {n} days re-priced from raw CSVs; largest difference vs harness Rs{w:.6f}")
        assert w < 0.01
