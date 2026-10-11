"""Paper trader: runs strategy.py on a live (or replayed) bar stream with the SAME engine, costs and
risk limits as the backtest. Simulated fills only - there is deliberately no order-placement code.

  python paper.py --replay          # demo on fake bars, no Kite needed
  python live_feed.py               # live NIFTY futures ticks -> 5-minute bars -> this trader
Halt a running session: create the file named by KILL_FILE (default ./KILL).
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from costs import CostModel
from engine import EngineParams, Risk, SessionEngine

import lifecycle

KILL_FILE = str(Path(__file__).parent / "KILL")


class PaperTrader:
    def __init__(self, module, name, costs=None, risk=None):
        self.m, self.name = module, name
        self.costs = costs or CostModel()
        self.risk = risk or Risk(kill_file=KILL_FILE)
        self.params = EngineParams(**module.ENGINE)
        lifecycle.LOGS.mkdir(parents=True, exist_ok=True)
        self.log = lifecycle.LOGS / f"{name}_trades.csv"
        self.daily = lifecycle.LOGS / f"{name}_daily.csv"
        self.eng, self.day, self.last_ts, self.logged = None, None, None, 0

    def on_bar(self, ts, o, h, l, c):
        if ts.date() != self.day:
            self.end_session()
            self.day = ts.date()
            self.eng = SessionEngine(self.m.make(), self.params, self.costs, self.risk)
            self.logged = 0
        self.last_ts = ts
        self.eng.on_bar(ts, o, h, l, c)
        self._flush()

    def end_session(self):
        if self.eng is not None:
            self.eng.finish(self.last_ts)
            self._flush()
            fresh = not self.daily.exists()
            with self.daily.open("a") as fh:
                if fresh:
                    fh.write("day,n_trades,pnl_rs\n")
                fh.write(f"{self.day},{len(self.eng.trades)},{self.eng.pnl_rs:.2f}\n")
            print(f"[{self.name}] {self.day}: {len(self.eng.trades)} trades, net Rs {self.eng.pnl_rs:,.0f}")
            self.eng = None

    def _flush(self):
        new = self.eng.trades[self.logged :]
        if not new:
            return
        fresh = not self.log.exists()
        with self.log.open("a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(new[0]))
            if fresh:
                w.writeheader()
            w.writerows(new)
        self.logged += len(new)


class Fleet:
    """Champion (+ challenger, if one is under test) fed the same bars."""

    def __init__(self):
        self.traders = [PaperTrader(m, n) for n, m in lifecycle.active_strategies()]

    def on_bar(self, ts, o, h, l, c):
        for t in self.traders:
            t.on_bar(ts, o, h, l, c)

    def end_session(self):
        for t in self.traders:
            t.end_session()


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--replay", action="store_true")
    a = a.parse_args()
    if not a.replay:
        raise SystemExit("Use live_feed.py for live data, or --replay for a demo.")
    from synth import synthetic_intraday
    pt = Fleet()
    for r in synthetic_intraday(n_days=5, phi=0.3).itertuples():
        pt.on_bar(r.date, r.open, r.high, r.low, r.close)
    pt.end_session()
