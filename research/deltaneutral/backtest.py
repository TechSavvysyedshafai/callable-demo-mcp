"""Mechanical backtest of the "intraday delta neutral" routine (docs/strategies/reyaansh_delta_neutral_intraday.md) on REAL NIFTY weekly
option candles. PAPER RESEARCH ONLY: this file contains no order placement of any kind; it replays saved candles.

Variants (pre-registered in research/RESULTS.md, 3 trials, no tuning):
  A  as taught: naked 25-delta short strangle, 25% re-matching adjustments, 30% stop at the straddle stage, range exit -> exit everything.
  B  as A, but on a confirmed breakout buy back only the threatened leg; the other leg stays with a cost-to-cost stop; exit 15:15 otherwise.
  C  as A, plus protective wings 200 points beyond each short strike bought at entry and held to the exit (never adjusted).

Timing: a decision is taken on the CLOSE of a 5-minute bar (only candles that START at or before that bar are used); the order fills at the
NEXT 5-minute candle OPEN (sold legs: open - slippage, bought legs: open + slippage). If the needed candle is missing the action is skipped
and counted. Mark of a held leg = last known 5-minute close at or before the decision bar.

Interpretations fixed BEFORE running (the doc is discretionary in places):
  I1  Entry decision at the close of the 09:40 bar (known 09:45), fill at the 09:45 open; no retry if the entry cannot be filled (day skipped).
  I2  25-delta: Black-Scholes delta with each strike's own implied vol inverted from its candle close at the decision bar; choose, per side, the strike
      with |delta| nearest to but not above 0.25 among strikes that have a candle in the decision bar.
  I3  Reference price of a leg starts at its sale fill. A leg trigger = mark >= 1.25 x reference. Adjustment: buy back the OTHER leg, sell a new option on that
      side whose candle close (decision bar) is nearest the risen leg's mark, from strikes at or beyond ATM (calls >= ATM, puts <= ATM, ATM = nearest 50).
      The risen leg's reference becomes its mark; the new leg's reference is its actual sale fill. If the best match is the current strike, only references are reset.
      One adjustment per bar. Both orders need a candle at the fill bar, else the adjustment is skipped and counted (it is re-evaluated on the next bar).
  I4  Straddle stage = both short strikes equal after an adjustment. Then 25% adjustments stop and each leg gets a stop at 1.30 x its reference; if either mark
      reaches it, exit everything.
  I5  Breakout = two consecutive 15-minute closes beyond the same boundary of the swing zone (zone fixed at entry). A: exit all. B: buy back only the threatened
      leg (call if up-breakout, put if down-breakout); the other leg exits when its mark >= its sale fill (cost-to-cost) or at 15:15.
  I6  Final exit decided on the 15:10 bar, filled at the 15:15 open; missing candles are retried bar by bar; if still open at the last bar, close at the last known
      close (+/- slippage) and count it. Nothing is ever held to expiry, so settlement STT does not arise (see settlement_stt for the rule if it did).
  I7  Priority per bar: EOD > straddle stop > breakout / cost-to-cost > adjustment.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scalp" / "options"))
import delta as dl  # noqa: E402
from costs_opt import OptionCostModel  # noqa: E402

FIVE = timedelta(minutes=5)
SESSION_OPEN = time(9, 15)


@dataclass
class Params:
    qty: int = 75  # 1 NIFTY lot (lot size as used elsewhere in this repo; unverified for the whole window)
    entry_decision: time = time(9, 40)  # bar start; its close (09:45) is when the entry is decided
    eod_decision: time = time(15, 10)  # bar start; fills at the 15:15 open
    entry_delta: float = 0.25
    adj_trigger: float = 0.25
    straddle_stop: float = 0.30
    wing_points: int = 200
    strike_step: int = 50
    breakout_closes: int = 2


def settlement_stt(intrinsic_pts: float, qty: int, rate: float = 0.0015) -> float:
    """STT on an option EXERCISED/settled in the money: rate x intrinsic value x qty. Rate 0.15% from the 2026 Budget change
    (was 0.125%) per an Upstox explainer read 2026-10-18; payer (buyer) is background knowledge, not verified. Unused by the backtest, which never holds to expiry."""
    return rate * max(intrinsic_pts, 0.0) * qty


class DaySim:
    def __init__(self, variant, bars, supp, resi, book, expiry, cm: OptionCostModel, p: Params, entry_cache: dict | None = None):
        assert variant in ("A", "B", "C")
        self.v, self.book, self.expiry, self.cm, self.p = variant, book, expiry, cm, p
        self.entry_cache = entry_cache  # evaluate.py only: entry strikes do not depend on variant or slippage
        self.ts = list(pd.to_datetime(bars["date"]))
        self.o = bars["open"].to_numpy(float)
        self.c = bars["close"].to_numpy(float)
        self.supp, self.resi = supp, resi
        self.day = self.ts[0].date() if self.ts else None
        self.cash = self.costs = 0.0
        self.orders = 0
        self.events: list[dict] = []
        self.legs: dict[str, dict] = {}
        self.wings: dict[str, dict] = {}
        self.pending = None
        self.mode = "strangle"  # strangle | straddle | hold
        self.done = False
        self.end_reason = None
        self.breakout = False
        self.run_n, self.last_dir = 0, 0
        self.n_adjust = self.n_noop = self.skipped_adjust = self.skipped_exit = self.forced = 0
        self.max_width = 0.0
        self.entry_info: dict = {}

    # ----- accounting -----
    def _order(self, px: float, is_buy: bool):
        self.cash += (-px if is_buy else px) * self.p.qty
        self.costs += self.cm.side(px, self.p.qty, is_buy)
        self.orders += 1

    def _sell_px(self, op: float) -> float:
        return max(op - self.cm.slippage_rs, 0.05)

    def _buy_px(self, op: float) -> float:
        return op + self.cm.slippage_rs

    def _ev(self, kind, dec_ts, fill_ts, **kw):
        self.events.append(dict(kind=kind, decision_ts=dec_ts, fill_ts=fill_ts, **kw))

    def _mark(self, key, j):
        return self.book.last_close(key, self.ts[j])

    # ----- entry -----
    def _decide_entry(self, i0):
        p, spot = self.p, self.c[i0]
        T = dl.years_to_expiry(self.expiry, self.ts[i0] + FIVE)
        picks = {}
        for typ in ("CE", "PE"):
            best = None
            for K in self.book.strikes.get((self.expiry, typ), []):
                key = (self.expiry, K, typ)
                row = self.book.row(key, self.ts[i0])
                if row is None or row[3] <= 0:
                    continue
                d = dl.delta_from_price(float(row[3]), spot, K, T, typ == "CE")
                if d is None:
                    continue
                if abs(d) <= p.entry_delta + 1e-12 and (best is None or abs(d) > best[0]):
                    best = (abs(d), K)
            if best is None:
                return None
            picks[typ] = best
        return picks

    def _exec_entry(self, picks, j, i0):
        p, e = self.p, self.expiry
        want = {"CE": (e, picks["CE"][1], "CE"), "PE": (e, picks["PE"][1], "PE")}
        wing_keys = {}
        if self.v == "C":
            wing_keys = {"CE": (e, picks["CE"][1] + p.wing_points, "CE"), "PE": (e, picks["PE"][1] - p.wing_points, "PE")}
        rows = {n: self.book.row(k, self.ts[j]) for n, k in want.items()}
        wrows = {n: self.book.row(k, self.ts[j]) for n, k in wing_keys.items()}
        if any(r is None for r in rows.values()):
            return "no_entry_candle"
        if any(r is None for r in wrows.values()):
            return "wing_unavailable"
        for n, k in want.items():
            px = self._sell_px(float(rows[n][0]))
            self._order(px, False)
            self.legs[n] = dict(key=k, strike=k[1], typ=n, sale=px, ref=px)
        for n, k in wing_keys.items():
            px = self._buy_px(float(wrows[n][0]))
            self._order(px, True)
            self.wings[n] = dict(key=k, strike=k[1], typ=n, buy=px)
        self.entry_info = dict(call_strike=picks["CE"][1], put_strike=picks["PE"][1], call_delta=picks["CE"][0], put_delta=picks["PE"][0],
                               call_px=self.legs["CE"]["sale"], put_px=self.legs["PE"]["sale"])
        self._ev("enter", self.ts[i0], self.ts[j], call=picks["CE"][1], put=picks["PE"][1])
        self._width()
        return None

    def _width(self):
        if self.v == "C" and "CE" in self.legs and "PE" in self.legs:
            wc = max(self.wings["CE"]["strike"] - self.legs["CE"]["strike"], 0)
            wp = max(self.legs["PE"]["strike"] - self.wings["PE"]["strike"], 0)
            self.max_width = max(self.max_width, wc, wp)

    # ----- pending execution (fills at the open of bar j) -----
    def _exec_pending(self, j):
        kind = self.pending[0]
        if kind == "adjust":
            _, risen, other, new_key, target, dec_ts = self.pending
            self.pending = None
            rb = self.book.row(self.legs[other]["key"], self.ts[j])
            rn = self.book.row(new_key, self.ts[j])
            if rb is None or rn is None:
                self.skipped_adjust += 1
                self._ev("adjust_skipped", dec_ts, self.ts[j])
                return
            bpx, spx = self._buy_px(float(rb[0])), self._sell_px(float(rn[0]))
            self._order(bpx, True)
            self._order(spx, False)
            self.legs[other] = dict(key=new_key, strike=new_key[1], typ=other, sale=spx, ref=spx)
            self.legs[risen]["ref"] = target
            self.n_adjust += 1
            if self.legs["CE"]["strike"] == self.legs["PE"]["strike"]:
                self.mode = "straddle"
                for L in self.legs.values():
                    L["stop"] = (1 + self.p.straddle_stop) * L["ref"]
            self._ev("adjust", dec_ts, self.ts[j], risen=risen, new_strike=new_key[1], bought=bpx, sold=spx)
            self._width()
        elif kind == "exit":
            _, reason, names, dec_ts = self.pending
            left = []
            for nm in names:
                grp = self.wings if nm.startswith("w") else self.legs
                L = grp[nm.lstrip("w")]
                r = self.book.row(L["key"], self.ts[j])
                if r is None:
                    self.skipped_exit += 1
                    left.append(nm)
                    continue
                px = self._sell_px(float(r[0])) if nm.startswith("w") else self._buy_px(float(r[0]))
                self._order(px, not nm.startswith("w"))
                del grp[nm.lstrip("w")]
                self._ev("exit_leg", dec_ts, self.ts[j], leg=nm, reason=reason, px=px)
            if left:
                self.pending = ("exit", reason, left, dec_ts)
            else:
                self.pending = None
                if reason == "range_exit" and self.v == "B":
                    self.mode = "hold"
                    self.breakout = True
                if not self.legs and not self.wings:
                    self.done, self.end_reason = True, reason

    # ----- decisions (made on the close of bar j) -----
    def _decide(self, j):
        p, now = self.p, self.ts[j]
        if now.time() >= p.eod_decision:
            self.pending = ("exit", "eod", self._all_names(), now)
            return
        # 15-minute close bookkeeping (a 15-minute bar ends when (minutes since 09:15 + 5) is a multiple of 15)
        mins = (now.hour * 60 + now.minute) - (SESSION_OPEN.hour * 60 + SESSION_OPEN.minute)
        if self.mode != "hold" and (mins + 5) % 15 == 0:
            cl = self.c[j]
            d = 1 if cl > self.resi else (-1 if cl < self.supp else 0)
            self.run_n = (self.run_n + 1 if d == self.last_dir else 1) if d != 0 else 0
            self.last_dir = d
        marks = {n: self._mark(L["key"], j) for n, L in self.legs.items()}
        if any(m is None for m in marks.values()):
            return
        if self.mode == "straddle" and any(marks[n] >= self.legs[n]["stop"] for n in self.legs):
            self.pending = ("exit", "straddle_stop", self._all_names(), now)
            return
        if self.mode == "hold":
            (n, L), = self.legs.items()
            if marks[n] >= L["sale"]:
                self.pending = ("exit", "cost_to_cost", self._all_names(), now)
            return
        if self.run_n >= p.breakout_closes:
            if self.v == "B":
                threatened = "CE" if self.last_dir > 0 else "PE"
                self.pending = ("exit", "range_exit", [threatened], now)
                self.breakout = True
            else:
                self.pending = ("exit", "range_exit", self._all_names(), now)
            return
        if self.mode == "strangle":
            ratio = {n: marks[n] / self.legs[n]["ref"] for n in self.legs}
            trig = [n for n in ratio if ratio[n] >= 1 + p.adj_trigger]
            if not trig:
                return
            risen = max(trig, key=lambda n: ratio[n])
            other = "PE" if risen == "CE" else "CE"
            target = marks[risen]
            atm = round(self.c[j] / p.strike_step) * p.strike_step
            best = None
            for K in self.book.strikes.get((self.expiry, other), []):
                if (other == "CE" and K < atm) or (other == "PE" and K > atm):
                    continue
                r = self.book.row((self.expiry, K, other), now)
                if r is None or r[3] <= 0:
                    continue
                score = (abs(float(r[3]) - target), -abs(K - atm))  # tie -> further from ATM
                if best is None or score < best[0]:
                    best = (score, K)
            if best is None:
                self.skipped_adjust += 1
                self._ev("adjust_skipped", now, None, why="no_candidate")
                return
            if best[1] == self.legs[other]["strike"]:
                self.n_noop += 1
                self.legs[risen]["ref"] = target
                self.legs[other]["ref"] = marks[other]
                self._ev("rematch_noop", now, None)
                return
            self.pending = ("adjust", risen, other, (self.expiry, best[1], other), target, now)

    def _all_names(self):
        return list(self.legs) + ["w" + k for k in self.wings]

    # ----- driver -----
    def run(self) -> dict:
        res = dict(variant=self.v, day=self.day, expiry=self.expiry, status="skipped", reason=None)
        if not self.ts:
            res["reason"] = "no_index_bars"
            return res
        try:
            i0 = self.ts.index(datetime.combine(self.day, self.p.entry_decision))
        except ValueError:
            res["reason"] = "no_entry_bar"
            return res
        if i0 + 1 >= len(self.ts):
            res["reason"] = "no_entry_bar"
            return res
        ck = (self.expiry, self.ts[i0])
        if self.entry_cache is not None and ck in self.entry_cache:
            picks = self.entry_cache[ck]
        else:
            picks = self._decide_entry(i0)
            if self.entry_cache is not None:
                self.entry_cache[ck] = picks
        if picks is None:
            res["reason"] = "no_strike"
            return res
        self.pending = ("enter", picks)
        for j in range(i0 + 1, len(self.ts)):
            if self.pending is not None:
                if self.pending[0] == "enter":
                    why = self._exec_entry(self.pending[1], j, i0)
                    self.pending = None
                    if why:
                        res["reason"] = why
                        return res
                else:
                    self._exec_pending(j)
            if self.done:
                break
            if self.pending is None and j < len(self.ts) - 1:
                self._decide(j)
        if not self.done:  # forced close at the last known close (should be rare; counted)
            j = len(self.ts) - 1
            for n, L in list(self.legs.items()):
                m = self._mark(L["key"], j)
                self._order(self._buy_px(m if m is not None else L["sale"]), True)
                self.forced += 1
            for n, L in list(self.wings.items()):
                m = self._mark(L["key"], j)
                self._order(self._sell_px(m if m is not None else L["buy"]), False)
                self.forced += 1
            self.legs, self.wings = {}, {}
            self.end_reason = "forced_close"
        res.update(status="traded", reason=None, gross=self.cash, cost=self.costs, net=self.cash - self.costs,
                   orders=self.orders, n_adjust=self.n_adjust, n_noop=self.n_noop, skipped_adjust=self.skipped_adjust,
                   skipped_exit=self.skipped_exit, forced=self.forced, end_reason=self.end_reason, breakout=self.breakout,
                   max_width_pts=self.max_width, entry=self.entry_info, events=self.events, dte=(self.expiry - self.day).days)
        return res


def run_day(variant, bars, supp, resi, book, expiry, cm: OptionCostModel, p: Params | None = None, entry_cache: dict | None = None) -> dict:
    return DaySim(variant, bars, supp, resi, book, expiry, cm, p or Params(), entry_cache).run()


def hedge_max_loss(short_call: float, short_put: float, wing_call: float, wing_put: float, credit_pts: float, qty: int) -> float:
    """Worst INTRADAY loss in rupees (before trading costs, before slippage on the exit fills) of the hedged structure if nothing is adjusted.
    A vertical spread can never be worth more than its strike width, so each side loses at most its width; intraday BOTH spreads can carry value at once
    (only one can be in the money at expiry), so the bound is the SUM of the two widths minus the net premium received (shorts sold minus wings bought)."""
    width = max(wing_call - short_call, 0) + max(short_put - wing_put, 0)
    return max(width - credit_pts, 0.0) * qty


def hedge_max_loss_at_expiry(short_call: float, short_put: float, wing_call: float, wing_put: float, credit_pts: float, qty: int) -> float:
    """Worst loss if the unadjusted hedged structure were HELD TO EXPIRY (only one side can finish in the money): the wider spread minus the net credit."""
    return max(max(wing_call - short_call, short_put - wing_put) - credit_pts, 0.0) * qty
