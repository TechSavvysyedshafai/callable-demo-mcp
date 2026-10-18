"""Plumbing test for the REAL-candle option backtest, using fake option files built from synthetic index bars."""

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent.parent
for p in (HERE / "options", HERE, HERE.parent):
    sys.path.insert(0, str(p))
import numpy as np
import pandas as pd

import bs
import real_backtest as rb
from contracts import UNDERLYINGS, next_expiry, years_to_expiry
from option_book import OptionBook
from synth import synthetic_intraday


def make_files(df, folder, cfg, iv=0.16):
    days = sorted(df["date"].dt.date.unique())
    expiries = sorted({next_expiry(cfg, d) for d in days})
    for ex in expiries:
        win = df[(df["date"].dt.date >= ex - timedelta(days=9)) & (df["date"].dt.date <= ex)]
        if win.empty:
            continue
        lo, hi = int(win["low"].min() // 50 * 50 - 200), int(win["high"].max() // 50 * 50 + 250)
        for k in range(lo, hi, 50):
            for typ in ("CE", "PE"):
                rows = []
                for r in win.itertuples():
                    T = years_to_expiry(ex, r.date)
                    call = typ == "CE"
                    f = lambda s: bs.price(s, k, T, iv, call)
                    a, b = (r.low, r.high) if call else (r.high, r.low)
                    rows.append([r.date, f(r.open), f(b), f(a), f(r.close), 100, 1000])
                pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "oi"]).to_csv(
                    folder / f"{ex}_{k}{typ}.csv", index=False)
    return expiries


cfg = dict(UNDERLYINGS["NIFTY"])
results = {}
for phi in (0.0, 0.5):
    df = synthetic_intraday(n_days=70, phi=phi, bar_vol=0.0008, seed=5)
    with tempfile.TemporaryDirectory() as d:
        folder = Path(d)
        cfg["calendar"] = make_files(df, folder, cfg)
        book = OptionBook(folder)
        assert len(book) > 100 and book.pick(cfg["calendar"][2], "CE", 24000, 200) is not None
        res = rb.evaluate(df, book, cfg, trials=1, runs=30)
        results[phi] = res
        print(phi, res["verdict"], "trades", res["n_trades"], "skipped", res["skipped_signals"],
              "net", round(res["net_rs"]), "p", round(res["p_vs_random_entries"], 3))
assert results[0.5]["n_trades"] > 20 and results[0.5]["net_rs"] > results[0.0]["net_rs"]
print("real backtest plumbing ok")
