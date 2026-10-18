"""Option-buying scalp session driven by the index-bar signal but priced with REAL option candles.
Rules (all conservative): decide at an index bar's close; buy at the NEXT bar's option open + slippage (if the option
did not trade in that bar, skip the trade); stop/target in % of entry premium checked on the option's own high/low
(stop first if both); a missing candle gives no information; forced flat by 15:15 at the bar close (or last known price)
minus slippage. There is no bid/ask in the candles, so slippage_rs is an ASSUMED half-spread - the weakest input."""

from __future__ import annotations

import os
from datetime import timedelta

import numpy as np

from contracts import next_expiry
from opt_engine import CAP, OptParams


class RealOptionSession:
    def __init__(self, strategy, params: OptParams, cfg: dict, costs, book, risk, max_gap: float | None = None):
        self.s, self.p, self.cfg, self.cm, self.book, self.risk = strategy, params, cfg, costs, book, risk
        self.max_gap = max_gap if max_gap is not None else cfg["step"]
        self.qty = cfg["lot"] * params.lots
        self.o, self.h, self.l, self.c = (np.empty(CAP) for _ in range(4))
        self.n, self.key, self.pending, self.halted, self.pnl_rs = 0, None, None, False, 0.0
        self.trades: list[dict] = []
        self.skipped = {"no_contract": 0, "no_entry_bar": 0}

    def _close(self, ts, px, why):
        gross = px - self.entry
        cost = self.cm.round_trip(self.entry, px, self.qty)
        net = gross * self.qty - cost
        self.trades.append({"entry_ts": self.entry_ts, "exit_ts": ts, "dir": 1 if self.key[2] == "CE" else -1,
                            "strike": self.key[1], "expiry": self.key[0], "entry": self.entry, "exit": px,
                            "gross_pts": gross, "cost_rs": cost, "net_rs": net, "why": why})
        self.pnl_rs += net
        self.key = None
        if self.pnl_rs <= -self.risk.max_daily_loss_rs:
            self.halted = True

    def _flat_price(self, ts, row):
        last = float(row[3]) if row is not None else self.book.last_close(self.key, ts)
        return max((last if last is not None else self.entry) - self.cm.slippage_rs, 0.0)

    def on_bar(self, ts, o, h, l, c):
        i, p, slip = self.n, self.p, self.cm.slippage_rs
        self.o[i], self.h[i], self.l[i], self.c[i] = o, h, l, c
        self.n += 1
        t, day = ts.time(), ts.date()
        if self.risk.kill_file and os.path.exists(self.risk.kill_file):
            self.halted = True

        if self.pending:
            kind, self.pending = self.pending, None
            if kind[0] == "enter" and self.key is None:
                e = next_expiry(self.cfg, day)
                if (e - day).days < p.min_dte_days:
                    e = next_expiry(self.cfg, e + timedelta(days=1))
                key = self.book.pick(e, "CE" if kind[1] > 0 else "PE", o, self.max_gap)
                if key is None:
                    self.skipped["no_contract"] += 1
                else:
                    row = self.book.row(key, ts)
                    entry = float(row[0]) + slip if row is not None else None
                    if entry is None or entry < p.min_premium:
                        self.skipped["no_entry_bar"] += 1
                    else:
                        self.key, self.entry, self.entry_i, self.entry_ts = key, entry, i, ts
                        self.stop, self.target = entry * (1 - p.stop_pct), entry * (1 + p.target_pct)
            elif kind[0] == "exit" and self.key is not None:
                row = self.book.row(self.key, ts)
                if row is not None:
                    self._close(ts, max(float(row[0]) - slip, 0.0), "time")
                else:
                    self.pending = ("exit",)  # nothing traded this bar: keep trying

        if self.key is not None:
            row = self.book.row(self.key, ts)
            if row is not None:
                if row[0] <= self.stop: self._close(ts, max(row[0] - slip, 0.0), "stop_gap")
                elif row[2] <= self.stop: self._close(ts, max(self.stop - slip, 0.0), "stop")
                elif row[1] >= self.target: self._close(ts, self.target, "target")

        if self.key is not None:
            if t >= p.flatten_at or self.halted:
                self._close(ts, self._flat_price(ts, self.book.row(self.key, ts)), "eod" if not self.halted else "halt")
            elif i - self.entry_i >= p.max_hold and self.pending is None:
                self.pending = ("exit",)

        if (self.key is None and self.pending is None and not self.halted and t < p.no_entry_after
                and len(self.trades) < self.risk.max_trades_per_day and i >= p.warmup):
            d = self.s.on_bar(self.o[: i + 1], self.h[: i + 1], self.l[: i + 1], self.c[: i + 1])
            if d:
                self.pending = ("enter", 1 if d > 0 else -1)

    def finish(self, ts):
        if self.key is not None:
            self._close(ts, self._flat_price(ts, self.book.row(self.key, ts)), "eod")
