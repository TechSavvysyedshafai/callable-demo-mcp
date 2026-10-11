"""Quote-driven option paper trader: signals come from INDEX bars (same strategy.py), but fills use real
option quotes - buy at the ask, sell at the bid - so the true spread is paid. Stop/target in % of the entry
premium, checked on every quote. Simulated fills only; no order-placement code exists in this repo."""

from __future__ import annotations

import csv
import os
from pathlib import Path

import numpy as np

from contracts import UNDERLYINGS
from costs_opt import OptionCostModel
from engine import Risk
from opt_engine import OptParams

CAP = 800


def pick_contract(rows: list[dict], name: str, spot: float, opt_type: str, today, min_dte: int):
    """Nearest-expiry (>= min_dte days away) ATM contract from Kite's instruments dump rows."""
    cands = [r for r in rows if r["name"] == name and r["instrument_type"] == opt_type]
    exps = sorted({r["expiry"] for r in cands})
    exps = [e for e in exps if (_d(e) - today).days >= min_dte]
    if not exps:
        return None
    same = [r for r in cands if r["expiry"] == exps[0]]
    return min(same, key=lambda r: abs(float(r["strike"]) - spot))


def _d(s):
    from datetime import date
    return s if hasattr(s, "year") else date.fromisoformat(str(s))


class QuotePaper:
    def __init__(self, strategy, params: OptParams, name: str, resolve, subscribe=lambda tok: None,
                 costs=None, risk=None, log: Path | None = None):
        self.s, self.p, self.name = strategy, params, name
        self.resolve, self.subscribe = resolve, subscribe  # resolve(dir, spot, ts) -> contract dict | None
        self.cm = costs or OptionCostModel(slippage_rs=0.0)  # spread is paid via bid/ask, not a slippage guess
        self.risk = risk or Risk()
        self.log = log
        self.o, self.h, self.l, self.c = (np.empty(CAP) for _ in range(4))
        self.n = 0
        self.day = None
        self.want = None  # contract we intend to buy at the next ask
        self.pos = None  # {"tok","sym","qty","entry","stop","target","bar_i","ts"}
        self.exit_now = False
        self.trades: list[dict] = []
        self.pnl_rs, self.halted = 0.0, False

    # ---- index bars ----
    def on_index_bar(self, ts, o, h, l, c):
        if ts.date() != self.day:
            self.day, self.n, self.want, self.pos, self.exit_now = ts.date(), 0, None, None, False
            self.pnl_rs, self.halted, self.trades = 0.0, False, []
        i = self.n
        self.o[i], self.h[i], self.l[i], self.c[i] = o, h, l, c
        self.n += 1
        t = ts.time()
        if self.risk.kill_file and os.path.exists(self.risk.kill_file):
            self.halted = True
        if self.want and i - self.want["i"] >= 2:  # never got a quote in time: cancel the stale entry
            self.want = None
        if self.pos:
            if t >= self.p.flatten_at or self.halted or i - self.pos["bar_i"] >= self.p.max_hold:
                self.exit_now = True
            return
        if (self.want is None and not self.halted and t < self.p.no_entry_after and i >= self.p.warmup
                and len(self.trades) < self.risk.max_trades_per_day):
            d = self.s.on_bar(self.o[: i + 1], self.h[: i + 1], self.l[: i + 1], self.c[: i + 1])
            if d:
                k = self.resolve(1 if d > 0 else -1, c, ts)
                if k:
                    self.want = {"i": i, **k}
                    self.subscribe(int(k["instrument_token"]))

    # ---- option quotes ----
    def on_quote(self, tok: int, ts, bid: float, ask: float):
        if self.want and tok == int(self.want["instrument_token"]) and self.pos is None:
            if ask <= 0 or ask < self.p.min_premium or ts.time() >= self.p.flatten_at:
                self.want = None
                return
            qty = int(self.want.get("lot_size", UNDERLYINGS["NIFTY"]["lot"])) * self.p.lots
            self.pos = {"tok": tok, "sym": self.want["tradingsymbol"], "qty": qty, "entry": ask, "ts": ts,
                        "stop": ask * (1 - self.p.stop_pct), "target": ask * (1 + self.p.target_pct),
                        "bar_i": self.want["i"] + 1}
            self.want, self.exit_now = None, False
            return
        if self.pos and tok == self.pos["tok"] and bid > 0:
            why = None
            if self.exit_now or ts.time() >= self.p.flatten_at or self.halted:
                why, px = ("eod" if ts.time() >= self.p.flatten_at else "time"), bid
            elif bid <= self.pos["stop"]:
                why, px = "stop", bid
            elif bid >= self.pos["target"]:
                why, px = "target", self.pos["target"]
            if why:
                self._close(ts, px, why)

    def _close(self, ts, px, why):
        q = self.pos
        gross = px - q["entry"]
        cost = self.cm.round_trip(q["entry"], px, q["qty"])
        net = gross * q["qty"] - cost
        row = {"entry_ts": q["ts"], "exit_ts": ts, "symbol": q["sym"], "qty": q["qty"], "entry": q["entry"],
               "exit": px, "gross_pts": gross, "cost_rs": cost, "net_rs": net, "why": why}
        self.trades.append(row)
        self.pnl_rs += net
        self.pos, self.exit_now = None, False
        if self.pnl_rs <= -self.risk.max_daily_loss_rs:
            self.halted = True
        if self.log:
            self.log.parent.mkdir(parents=True, exist_ok=True)
            fresh = not self.log.exists()
            with self.log.open("a", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(row))
                if fresh:
                    w.writeheader()
                w.writerow(row)
