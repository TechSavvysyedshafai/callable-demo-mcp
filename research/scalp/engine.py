"""One trading session, bar by bar. The SAME class runs the backtest and the paper trader,
so they cannot drift apart. Decisions are made at a bar's close and filled at the NEXT bar's
open (+slippage); stops fill at the stop (+slippage, or the open on a gap); if a bar touches
both stop and target the stop is assumed first. No real orders are ever sent from here."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time

import numpy as np

CAP = 800


@dataclass
class EngineParams:
    stop_k: float = 1.5  # stop distance = stop_k * sigma (std of recent bar-to-bar price changes)
    target_k: float = 2.0
    max_hold: int = 12  # bars
    sigma_window: int = 20
    no_entry_after: time = time(15, 0)
    flatten_at: time = time(15, 15)
    lots: int = 1


@dataclass
class Risk:
    max_daily_loss_rs: float = 5000.0
    max_trades_per_day: int = 20
    kill_file: str | None = None  # create this file to halt a live/paper session


class SessionEngine:
    def __init__(self, strategy, params: EngineParams, costs, risk: Risk):
        self.s, self.p, self.costs, self.risk = strategy, params, costs, risk
        self.qty = costs.lot_size * params.lots
        self.o, self.h, self.l, self.c = (np.empty(CAP) for _ in range(4))
        self.n = 0
        self.pos = 0
        self.entry = self.stop = self.target = 0.0
        self.entry_i = 0
        self.entry_ts = None
        self.pending = None
        self.trades: list[dict] = []
        self.pnl_rs = 0.0
        self.halted = False

    # ---- internals ----
    def _close(self, ts, px, why):
        d = self.pos
        gross = d * (px - self.entry)
        cost = self.costs.round_trip(self.entry, px, d, self.qty)
        net = gross * self.qty - cost
        self.trades.append({"entry_ts": self.entry_ts, "exit_ts": ts, "dir": d, "entry": self.entry,
                            "exit": px, "gross_pts": gross, "cost_rs": cost, "net_rs": net, "why": why})
        self.pnl_rs += net
        self.pos = 0
        if self.pnl_rs <= -self.risk.max_daily_loss_rs:
            self.halted = True

    # ---- public ----
    def on_bar(self, ts, o, h, l, c):
        i = self.n
        self.o[i], self.h[i], self.l[i], self.c[i] = o, h, l, c
        self.n += 1
        t, slip, p = ts.time(), self.costs.slippage_pts, self.p
        if self.risk.kill_file and os.path.exists(self.risk.kill_file):
            self.halted = True

        if self.pending:  # 1. fill what was decided on the previous close
            kind, self.pending = self.pending, None
            if kind[0] == "enter" and self.pos == 0:
                d, sig = kind[1], kind[2]
                self.pos, self.entry, self.entry_i, self.entry_ts = d, o + d * slip, i, ts
                self.stop = self.entry - d * p.stop_k * sig
                self.target = self.entry + d * p.target_k * sig
            elif kind[0] == "exit" and self.pos != 0:
                self._close(ts, o - self.pos * slip, "time")

        if self.pos > 0:  # 2. stop / target inside this bar (stop first if both)
            if o <= self.stop: self._close(ts, o - slip, "stop_gap")
            elif l <= self.stop: self._close(ts, self.stop - slip, "stop")
            elif h >= self.target: self._close(ts, self.target, "target")
        elif self.pos < 0:
            if o >= self.stop: self._close(ts, o + slip, "stop_gap")
            elif h >= self.stop: self._close(ts, self.stop + slip, "stop")
            elif l <= self.target: self._close(ts, self.target, "target")

        if self.pos != 0:  # 3. end of day / halt / time stop
            if t >= p.flatten_at or self.halted:
                self._close(ts, c - self.pos * slip, "eod" if not self.halted else "halt")
            elif i - self.entry_i >= p.max_hold:
                self.pending = ("exit",)

        if (self.pos == 0 and self.pending is None and not self.halted and t < p.no_entry_after
                and len(self.trades) < self.risk.max_trades_per_day and i >= p.sigma_window + 1):
            d = self.s.on_bar(self.o[: i + 1], self.h[: i + 1], self.l[: i + 1], self.c[: i + 1])
            if d:
                sig = float(np.std(np.diff(self.c[i - p.sigma_window : i + 1])))
                if sig > 0:
                    self.pending = ("enter", 1 if d > 0 else -1, sig)

    def finish(self, ts):
        """Call after the last bar of the session."""
        if self.pos != 0:
            self._close(ts, self.c[self.n - 1] - self.pos * self.costs.slippage_pts, "eod")
