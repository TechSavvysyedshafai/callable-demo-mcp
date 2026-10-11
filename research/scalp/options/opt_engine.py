"""One session of option-BUYING scalps driven by an index-bar signal (+1 = buy ATM call, -1 = buy ATM put).
Premiums are MODEL-BASED (Black-Scholes from the index bar, India VIX as IV, IV held constant intraday),
so results are indicative only. Decide at bar close, fill at next open +/- half-spread, stop/target in % of
premium, stop first if a bar touches both, forced flat by 15:15. No orders are ever sent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time, timedelta

import numpy as np

import bs
from contracts import next_expiry, years_to_expiry

CAP = 800


@dataclass
class OptParams:
    stop_pct: float = 0.20
    target_pct: float = 0.30
    max_hold: int = 8  # bars
    warmup: int = 21  # bars before the signal may fire
    no_entry_after: time = time(15, 0)
    flatten_at: time = time(15, 15)
    lots: int = 1
    min_premium: float = 20.0
    min_dte_days: int = 1  # 1 = never open on expiry day (extreme gamma/theta); 0 allows it
    r: float = 0.065


class OptionSession:
    def __init__(self, strategy, params: OptParams, cfg: dict, costs, iv: float, risk):
        self.s, self.p, self.cfg, self.cm, self.iv, self.risk = strategy, params, cfg, costs, iv, risk
        self.qty = cfg["lot"] * params.lots
        self.o, self.h, self.l, self.c = (np.empty(CAP) for _ in range(4))
        self.n, self.pos, self.pending, self.halted, self.pnl_rs = 0, 0, None, False, 0.0
        self.trades: list[dict] = []

    def _prem(self, spot, ts):
        T = years_to_expiry(self.exp, ts)
        return bs.price(spot, self.K, T, self.iv, self.pos > 0, self.p.r)

    def _close(self, ts, px, why):
        gross = px - self.entry  # premium points; we only ever BUY options
        cost = self.cm.round_trip(self.entry, px, self.qty)
        net = gross * self.qty - cost
        self.trades.append({"entry_ts": self.entry_ts, "exit_ts": ts, "dir": self.pos, "strike": self.K,
                            "expiry": self.exp, "entry": self.entry, "exit": px, "gross_pts": gross,
                            "cost_rs": cost, "net_rs": net, "why": why})
        self.pnl_rs += net
        self.pos = 0
        if self.pnl_rs <= -self.risk.max_daily_loss_rs:
            self.halted = True

    def on_bar(self, ts, o, h, l, c):
        i, p, slip = self.n, self.p, self.cm.slippage_rs
        self.o[i], self.h[i], self.l[i], self.c[i] = o, h, l, c
        self.n += 1
        t, day = ts.time(), ts.date()
        if self.risk.kill_file and os.path.exists(self.risk.kill_file):
            self.halted = True

        if self.pending:
            kind, self.pending = self.pending, None
            if kind[0] == "enter" and self.pos == 0:
                e = next_expiry(self.cfg, day)
                if (e - day).days < p.min_dte_days:
                    e = next_expiry(self.cfg, e + timedelta(days=1))
                K = round(o / self.cfg["step"]) * self.cfg["step"]
                self.pos, self.K, self.exp = kind[1], K, e
                entry = self._prem(o, ts) + slip
                if entry < p.min_premium:
                    self.pos = 0
                else:
                    self.entry, self.entry_i, self.entry_ts = entry, i, ts
                    self.stop, self.target = entry * (1 - p.stop_pct), entry * (1 + p.target_pct)
            elif kind[0] == "exit" and self.pos != 0:
                self._close(ts, self._prem(o, ts) - slip, "time")

        if self.pos != 0:
            lo_s, hi_s = (l, h) if self.pos > 0 else (h, l)  # spot extremes that give the premium's low / high
            p_open, p_low, p_high = self._prem(o, ts), self._prem(lo_s, ts), self._prem(hi_s, ts)
            if p_open <= self.stop: self._close(ts, p_open - slip, "stop_gap")
            elif p_low <= self.stop: self._close(ts, self.stop - slip, "stop")
            elif p_high >= self.target: self._close(ts, self.target, "target")

        if self.pos != 0:
            if t >= p.flatten_at or self.halted:
                self._close(ts, self._prem(c, ts) - slip, "eod" if not self.halted else "halt")
            elif i - self.entry_i >= p.max_hold:
                self.pending = ("exit",)

        if (self.pos == 0 and self.pending is None and not self.halted and t < p.no_entry_after
                and len(self.trades) < self.risk.max_trades_per_day and i >= p.warmup):
            d = self.s.on_bar(self.o[: i + 1], self.h[: i + 1], self.l[: i + 1], self.c[: i + 1])
            if d:
                self.pending = ("enter", 1 if d > 0 else -1)

    def finish(self, ts):
        if self.pos != 0:
            self._close(ts, self._prem(self.c[self.n - 1], ts) - self.cm.slippage_rs, "eod")
