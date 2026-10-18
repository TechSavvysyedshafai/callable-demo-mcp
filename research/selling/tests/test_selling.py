"""SELL1 self-checks: payoff known answers, no-lookahead, costs incl. settlement STT, skipped weeks, stop logic, stats helpers.
Run:  python research/selling/tests/test_selling.py   (also collected by pytest)."""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import backtest as bt  # noqa: E402
import evaluate as ev  # noqa: E402
from costs_opt import OptionCostModel  # noqa: E402

ST = {"sc": (24800, "CE"), "lc": (24950, "CE"), "sp": (24200, "PE"), "lp": (24050, "PE")}
EXPIRY = date(2026, 1, 8)
D0, D1 = datetime(2026, 1, 1), datetime(2026, 1, 8)


def approx(a, b, tol=1e-6):
    assert abs(a - b) <= tol, (a, b)


def test_known_payoff():
    credit = 20.0
    # settle -> hand-computed P&L (points per unit): between the short strikes keep the credit; beyond a long strike lose width - credit
    for settle, want in [(24500, 20), (24800, 20), (24200, 20), (24900, 20 - 100), (24950, 20 - 150), (25100, 20 - 150),
                         (24100, 20 - 100), (24050, 20 - 150), (23000, 20 - 150), (24825, 20 - 25)]:
        approx(bt.condor_settle_pnl_points(ST, credit, settle), want)
    # max gain = credit, max loss = width - credit
    sweep = [bt.condor_settle_pnl_points(ST, credit, s) for s in range(22000, 27001, 5)]
    approx(max(sweep), credit)
    approx(min(sweep), -(bt.WING - credit))
    approx(bt.condor_settle_pnl_points(ST, credit, 24900) * bt.LOT, -80 * 75)  # rupees per lot


def test_strike_rules():
    assert bt.short_strikes(24500.0) == (24800, 24200)  # 24794 -> up to 24800 ; 24206 -> down to 24200
    assert bt.short_strikes(24000.0) == (24300, 23700)  # 24288 -> 24300 ; 23712 -> 23700
    assert bt.short_strikes(25000.0) == (25300, 24700)  # 25300 exactly stays; 24700 exactly stays
    st = bt.leg_strikes(24500.0)
    assert st["lc"] == (24950, "CE") and st["lp"] == (24050, "PE")


def test_entry_day_and_bar():
    days = [date(2025, 12, 25) + timedelta(days=i) for i in range(0, 16) if (date(2025, 12, 25) + timedelta(days=i)).weekday() < 5]
    assert bt.entry_day(date(2026, 1, 8), days) == date(2026, 1, 1)  # exactly 7 calendar days before
    days2 = [d for d in days if d != date(2026, 1, 1)]  # holiday on that date: nearest trading day on or before it
    assert bt.entry_day(date(2026, 1, 8), days2) == date(2025, 12, 31)
    assert bt.entry_day(date(2026, 1, 8), [date(2026, 1, 5)]) is None
    bars = _bars()
    i = bt.entry_bar(bars, date(2026, 1, 1))
    assert bars.loc[i, "date"] == datetime(2026, 1, 1, 9, 30)  # not 09:25
    assert bt.entry_bar(bars, date(2026, 1, 1), shift=1) == i + 1


def _bars(extra_closes=None):
    ts = []
    for d in (D0, D1):
        t = d.replace(hour=9, minute=15)
        while t <= d.replace(hour=15, minute=25):
            ts.append(t)
            t += timedelta(minutes=5)
    df = pd.DataFrame({"date": ts, "open": 24500.0, "high": 24510.0, "low": 24490.0, "close": 24500.0, "volume": 0})
    return df


def _leg(price_at, bars, base):
    """Option candles on the whole grid: open = close = base unless price_at overrides {timestamp: (open, close)}."""
    rows = []
    for t in bars["date"]:
        o, c = price_at.get(t, (base, base))
        rows.append({"date": t, "open": o, "high": max(o, c), "low": min(o, c), "close": c, "volume": 1, "oi": 1})
    return pd.DataFrame(rows).set_index("date")


def _legs(bars, over=None):
    over = over or {}
    base = {"sc": 10.0, "lc": 4.0, "sp": 12.0, "lp": 5.0}  # credit before slippage = 10 + 12 - 4 - 5 = 13
    return {n: _leg(over.get(n, {}), bars, base[n]) for n in bt.LEGS}


def _e_idx(bars):
    return bt.entry_bar(bars, date(2026, 1, 1))


def test_costs_and_settlement_stt():
    cm = OptionCostModel(slippage_rs=0.20)
    # independent hand calculation of one sell order: Rs10 x 75 = Rs750 turnover
    turn = 10 * 75
    exch, sebi = 0.0003553 * turn, 0.000001 * turn
    want = 20 + exch + sebi + 0.18 * (20 + exch + sebi) + 0.0015 * turn
    approx(cm.side(10, 75, False), want, 1e-9)
    # settlement STT: 0.15% x intrinsic x qty on EVERY ITM leg
    approx(bt.settlement_stt(ST, 24900), 0.0015 * 100 * 75)  # only the short call is ITM
    approx(bt.settlement_stt(ST, 25100), 0.0015 * (300 + 150) * 75)  # short and long call ITM
    approx(bt.settlement_stt(ST, 24000), 0.0015 * (200 + 50) * 75 + 0.0)  # puts: 24200-24000 and 24050-24000
    approx(bt.settlement_stt(ST, 24500), 0.0)
    # whole-week check, V1, expires worthless: fills = open -/+ 0.20 slippage, 4 orders at entry and NOTHING else
    bars = _bars()
    legs = _legs(bars)
    w = bt.simulate_week(EXPIRY, legs, bars, 24500.0, _e_idx(bars), "V1", cm, strikes=ST)
    assert w.skipped is None
    fills = {"sc": 9.8, "sp": 11.8, "lc": 4.2, "lp": 5.2}
    approx(w.credit, 9.8 + 11.8 - 4.2 - 5.2)
    cost = sum(cm.side(fills[n], 75, n in ("lc", "lp")) for n in bt.LEGS)
    approx(w.costs_rs, cost, 1e-9)
    approx(w.net_rs, w.credit * 75 - cost, 1e-9)
    # same week but the index settles at 24900 (short call ITM by 100): add settlement STT, lose 100 pts
    w2 = bt.simulate_week(EXPIRY, legs, bars, 24900.0, _e_idx(bars), "V1", cm, strikes=ST)
    approx(w2.costs_rs, cost + 0.0015 * 100 * 75, 1e-9)
    approx(w2.gross_pts, w.credit - 100)
    assert w2.breach and not w.breach


def test_no_lookahead():
    cm = OptionCostModel(slippage_rs=0.10)
    bars = _bars()
    e = _e_idx(bars)
    ets = bars.loc[e, "date"]
    over = {n: {ets: (v, v)} for n, v in zip(bt.LEGS, (10.0, 4.0, 12.0, 5.0))}
    legs = _legs(bars, over)
    base = bt.simulate_week(EXPIRY, legs, bars, 24500.0, e, "V1", cm, strikes=ST)
    # (1) change every candle AFTER the entry bar and every bar after it: entry fills, credit and strikes are unchanged
    legs2 = {n: df.copy() for n, df in legs.items()}
    for df in legs2.values():
        df.loc[df.index > ets, ["open", "close"]] = 99.0
    bars2 = bars.copy()
    bars2.loc[bars2.index > e, ["open", "close"]] = 30000.0
    again = bt.simulate_week(EXPIRY, legs2, bars2, 24500.0, e, "V1", cm, strikes=ST)
    assert again.credit == base.credit and again.spot == base.spot == 24500.0 and again.strikes == base.strikes
    # strikes derived from the entry bar's own data only
    bars3 = bars.copy()
    bars3.loc[e, "close"] = 24000.0
    assert bt.leg_strikes(bars3.loc[e, "close"]) != bt.leg_strikes(bars.loc[e, "close"])
    # (2) shifting the entry by one bar changes the fills to the NEXT bar's opens (and nothing earlier is used)
    nxt = bars.loc[e + 1, "date"]
    over2 = {n: {ets: (v, v), nxt: (v + (2 if n in ("sc", "sp") else 0),) * 2} for n, v in zip(bt.LEGS, (10.0, 4.0, 12.0, 5.0))}
    legs3 = _legs(bars, over2)
    s0 = bt.simulate_week(EXPIRY, legs3, bars, 24500.0, e, "V1", cm, strikes=ST)
    s1 = bt.simulate_week(EXPIRY, legs3, bars, 24500.0, e + 1, "V1", cm, strikes=ST)
    approx(s0.credit, 10 - .1 + 12 - .1 - 4 - .1 - 5 - .1)
    approx(s1.credit, s0.credit + 4.0)  # the two short legs open 2 higher on the next bar
    assert s1.entry_ts == nxt.to_pydatetime()


def test_skip_weeks():
    cm = OptionCostModel(slippage_rs=0.10)
    bars = _bars()
    e = _e_idx(bars)
    legs = _legs(bars)
    legs["lp"] = legs["lp"].drop(index=bars.loc[e, "date"])  # no candle for one leg at the entry bar
    w = bt.simulate_week(EXPIRY, legs, bars, 24500.0, e, "V1", cm, strikes=ST)
    assert w.skipped == "no_candle_at_entry" and np.isnan(w.net_rs)
    legs = _legs(bars)
    legs["sc"] = None
    assert bt.simulate_week(EXPIRY, legs, bars, 24500.0, e, "V1", cm, strikes=ST).skipped == "missing_option_file"
    assert bt.simulate_week(EXPIRY, _legs(bars), bars, None, e, "V1", cm, strikes=ST).skipped == "no_settlement_close"
    assert bt.simulate_week(EXPIRY, _legs(bars), bars, 24500.0, None, "V1", cm, strikes=ST).skipped == "no_entry_bar"
    # skipped weeks are counted and excluded from the P&L statistics
    ok = bt.simulate_week(EXPIRY, _legs(bars), bars, 24500.0, e, "V1", cm, strikes=ST)
    s = ev.summarize([w, ok, ok])
    assert s["weeks_traded"] == 2 and s["weeks_skipped"] == 1 and s["skip_reasons"] == {"no_candle_at_entry": 1}


def test_stop_logic():
    cm = OptionCostModel(slippage_rs=0.10)
    bars = _bars()
    e = _e_idx(bars)
    t = lambda k: bars.loc[e + k, "date"]  # noqa: E731
    credit = 10 - .1 + 12 - .1 - (4 + .1) - (5 + .1)  # = 12.6 after slippage; stop when mark cost - credit >= 25.2
    # at bar e+3 the short call close jumps to 40: mark cost = 40 + 12 - 4 - 5 = 43 ; loss = 43 - 12.6 = 30.4 >= 25.2 -> stop.
    # exit at the OPEN of bar e+4: sc open 41 (+0.1 buyback), lc open 6 (-0.1), sp 12 (+0.1), lp 5 (-0.1)
    over = {"sc": {t(3): (30.0, 40.0), t(4): (41.0, 41.0)}, "lc": {t(4): (6.0, 6.0)}}
    legs = _legs(bars, over)
    w = bt.simulate_week(EXPIRY, legs, bars, 24500.0, e, "V2", cm, strikes=ST)
    assert w.stopped and w.stop_ts == t(3).to_pydatetime(), (w.stopped, w.stop_ts)
    exit_cost = (41.1 + 12.1) - (5.9 + 4.9)
    approx(w.gross_pts, credit - exit_cost, 1e-9)
    entry_cost = sum(cm.side(f, 75, n in ("lc", "lp")) for n, f in zip(bt.LEGS, (9.9, 4.1, 11.9, 5.1)))
    exit_costs = sum(cm.side(f, 75, n in ("sc", "sp")) for n, f in zip(bt.LEGS, (41.1, 5.9, 12.1, 4.9)))
    approx(w.costs_rs, entry_cost + exit_costs, 1e-9)  # no settlement STT after a stop
    # V1 on identical data ignores the stop and settles at the index close
    v1 = bt.simulate_week(EXPIRY, legs, bars, 24500.0, e, "V1", cm, strikes=ST)
    assert not v1.stopped and abs(v1.gross_pts - credit) < 1e-9
    # a loss just under 2x credit (25.2) does NOT stop
    over_small = {"sc": {t(3): (30.0, 34.7)}}  # mark cost 34.7+12-4-5 = 37.7, loss 25.1 < 25.2
    w3 = bt.simulate_week(EXPIRY, _legs(bars, over_small), bars, 24500.0, e, "V2", cm, strikes=ST)
    assert not w3.stopped
    # the stop is evaluated on closes only: a spike in the HIGH never triggers it
    spike = _legs(bars)
    spike["sc"].loc[t(3), "high"] = 500.0
    assert not bt.simulate_week(EXPIRY, spike, bars, 24500.0, e, "V2", cm, strikes=ST).stopped
    # trigger on the very last bar: no later bar exists -> last known close with slippage
    last = len(bars) - 1
    tl = bars.loc[last, "date"]
    over_last = {"sc": {tl: (10.0, 60.0)}}
    wl = bt.simulate_week(EXPIRY, _legs(bars, over_last), bars, 24500.0, e, "V2", cm, strikes=ST)
    assert wl.stopped and wl.stop_ts == tl.to_pydatetime()
    approx(wl.gross_pts, credit - ((60.0 + .1) + (12.0 + .1) - (4.0 - .1) - (5.0 - .1)), 1e-9)


def test_stats_helpers():
    approx(bt.max_drawdown([5, -2, -3, 4, -10, 1]), -11.0)  # cumulative 5,3,0,4,-6,-5: peak 5 down to -6
    assert bt.max_drawdown([1, 1, 1]) == 0.0
    approx(bt.max_drawdown([-3, 2, -4]), -5.0)  # cumulative: -3, -1, -5 against a peak of 0
    assert ev.longest_losing_streak([1, -1, -2, -3, 4, -1]) == 3
    lo, hi = ev.block_bootstrap_ci(np.full(40, 5.0))
    assert lo == hi == 5.0
    rng = np.random.default_rng(1)
    lo, hi = ev.block_bootstrap_ci(rng.normal(0, 10, 80))
    assert lo < 0 < hi  # zero-mean noise: interval straddles zero
    lo, hi = ev.block_bootstrap_ci(rng.normal(50, 10, 80))
    assert lo > 0
    good = {"0.2": {"mean_net": 100.0, "ci90_lo": 10.0, "total_net": 3000.0, "worst_week": -1000.0}, "0.3": {"mean_net": 50.0}}
    assert ev.pass_rule(good)["useful"]
    bad = {"0.2": {"mean_net": 100.0, "ci90_lo": -10.0, "total_net": 3000.0, "worst_week": -1000.0}, "0.3": {"mean_net": 50.0}}
    assert not ev.pass_rule(bad)["useful"]
    tail = {"0.2": {"mean_net": 100.0, "ci90_lo": 10.0, "total_net": 1500.0, "worst_week": -1000.0}, "0.3": {"mean_net": 50.0}}
    assert not ev.pass_rule(tail)["useful"]  # total < 2 x worst week


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("ok", name)
    print(f"all {n} selling tests passed")
