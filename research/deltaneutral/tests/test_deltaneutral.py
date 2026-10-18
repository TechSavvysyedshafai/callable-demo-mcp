"""Tests for the delta-neutral study. Synthetic data only (no network, no holdout).
Run:  python3 research/deltaneutral/tests/test_deltaneutral.py   (also pytest-compatible)"""

import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # deltaneutral/
sys.path.insert(0, str(HERE.parents[1] / "scalp" / "options"))
import backtest as bt  # noqa: E402
import evaluate as ev  # noqa: E402
import delta as dl  # noqa: E402
import swing as sw  # noqa: E402
import bs  # noqa: E402
from costs_opt import OptionCostModel  # noqa: E402
from option_book import OptionBook  # noqa: E402

DAY, EXPIRY = date(2026, 1, 5), date(2026, 1, 9)
SPOT, IV = 24000.0, 0.15
STRIKES = list(range(23000, 25001, 50))
T0 = datetime(2026, 1, 5, 9, 15)
BARS = [T0 + timedelta(minutes=5 * i) for i in range(75)]  # 09:15 .. 15:25
I = {b.strftime("%H:%M"): i for i, b in enumerate(BARS)}  # bar index by start time


def _tick(x):
    return max(round(x * 20) / 20, 0.05)


def make_world(changes=(), spot_path=None, drop=(), strikes=STRIKES):
    """Flat synthetic day. Option prices are Black-Scholes at 09:45 and then frozen, except `changes` = [(bar_start 'HH:MM', typ, strike, price)] applied from that bar on.
    `spot_path` = {bar_start: close} overrides for index bars (each stays until changed). `drop` = {(typ, strike, 'HH:MM')} candles removed. Returns (bars_df, OptionBook)."""
    T = dl.years_to_expiry(EXPIRY, datetime(2026, 1, 5, 9, 45))
    base = {(t, K): _tick(bs.price(SPOT, K, T, IV, t == "CE")) for K in strikes for t in ("CE", "PE")}
    sp, cur = np.full(75, SPOT), SPOT
    for i, b in enumerate(BARS):
        cur = (spot_path or {}).get(b.strftime("%H:%M"), cur)
        sp[i] = cur
    bars = pd.DataFrame({"date": BARS, "open": sp, "high": sp, "low": sp, "close": sp})
    d = Path(tempfile.mkdtemp())
    for (t, K), p0 in base.items():
        px = np.full(75, p0)
        for hhmm, tt, kk, pp in sorted(changes, key=lambda x: I[x[0]]):
            if tt == t and kk == K:
                px[I[hhmm]:] = pp
        keep = [i for i, b in enumerate(BARS) if (t, K, b.strftime("%H:%M")) not in set(drop)]
        df = pd.DataFrame({"date": [BARS[i] for i in keep], "open": px[keep], "high": px[keep], "low": px[keep], "close": px[keep], "volume": 100, "oi": 1000})
        df.to_csv(d / f"{EXPIRY}_{K}{t}.csv", index=False)
    return bars, OptionBook(d), base


def sim(variant, bars, book, supp=23800.0, resi=24200.0, slip=0.10, p=None):
    s = bt.DaySim(variant, bars, supp, resi, book, EXPIRY, OptionCostModel(slippage_rs=slip), p or bt.Params())
    out = s.run()
    return s, out


def expected_entry(base):
    """Independent expectation: per side the strike with |BS delta| nearest to but not above 0.25 (deltas from the true generating IV)."""
    T = dl.years_to_expiry(EXPIRY, datetime(2026, 1, 5, 9, 45))
    out = {}
    for t in ("CE", "PE"):
        best = max((abs(bs.delta(SPOT, K, T, IV, t == "CE")), K) for K in STRIKES if abs(bs.delta(SPOT, K, T, IV, t == "CE")) <= 0.25)
        out[t] = best[1]
    return out


# ---------- swing detector: known answer ----------
def _bars15(highs, lows):
    n = len(highs)
    return pd.DataFrame({"date": pd.date_range("2026-01-01 09:15", periods=n, freq="15min"), "open": 0.0, "high": highs, "low": lows, "close": 0.0})


def test_swing_known_answer():
    # swing highs at index 3 (value 20) and 10 (value 18); swing lows at index 7 (value 1) and 14 (value 2)
    highs = [10, 11, 12, 20, 12, 11, 10, 9, 10, 11, 18, 11, 10, 9, 8, 9, 10, 11, 12]
    lows = [h - 5 for h in highs]
    lows[7], lows[14] = 1, 2
    hi, lo = sw.fractal_swings(np.array(highs), np.array(lows))
    assert hi == [20.0, 18.0], hi
    assert lo == [1.0, 2.0], lo
    # spot 12: nearest swing high ABOVE is 18, nearest swing low BELOW is 2 -> zone (2, 18); width 16/12 is far too wide -> None
    assert sw.swing_range(_bars15(highs, lows), 12.0) is None
    # scale to index-like levels: the same shape at 24000 with a 1% zone passes
    k = 24000.0
    hh = [k + x for x in [0, 1, 2, 120, 2, 1, 0, -1, 0, 1, 100, 1, 0, -1, -2, -1, 0, 1, 2]]
    ll = [h - 5 for h in hh]
    ll[7], ll[14] = k - 100, k - 120
    assert sw.fractal_swings(np.array(hh), np.array(ll)) == ([k + 120, k + 100], [k - 100, k - 120])
    z = sw.swing_range(_bars15(hh, ll), k)
    assert z == (k - 100, k + 100), z  # nearest above = 24100 (not 24120), nearest below = 23900 (not 23880); width 200/24000 = 0.83%
    # only one side available -> no trade
    assert sw.swing_range(_bars15(hh, ll), k + 500) is None
    # a tie is not a swing (strict)
    assert sw.fractal_swings(np.array([1, 2, 3, 5, 5, 3, 2, 1.0]), np.array([0.0] * 8))[0] == []


def test_swing_uses_only_prior_sessions():
    d5 = pd.DataFrame({"date": pd.date_range("2026-01-01 09:15", periods=75, freq="5min").append(pd.date_range("2026-01-02 09:15", periods=75, freq="5min")
                                                                                              .append(pd.date_range("2026-01-05 09:15", periods=75, freq="5min"))),
                       "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0})
    d15 = sw.resample_15m(d5)
    assert len(d15) == 75 // 3 * 3 and d15["date"].iloc[0].time().strftime("%H:%M") == "09:15"
    prev = sw.previous_sessions(d15, date(2026, 1, 5))
    assert prev["date"].dt.date.max() == date(2026, 1, 2)
    assert prev["date"].dt.date.nunique() == 2


# ---------- implied vol / delta round trip ----------
def test_iv_delta_roundtrip():
    T = dl.years_to_expiry(EXPIRY, datetime(2026, 1, 5, 9, 45))
    assert abs(T - (4 * 86400 + 5 * 3600 + 45 * 60) / (365 * 86400)) < 1e-12  # Mon 09:45 -> Fri 15:30 on expiry
    for iv in (0.08, 0.15, 0.40):
        for K, is_call in ((23700, False), (24300, True), (24000, True), (24000, False)):
            px = bs.price(SPOT, K, T, iv, is_call)
            got = dl.implied_vol(px, SPOT, K, T, is_call)
            assert abs(got - iv) < 1e-6, (iv, K, got)
            assert abs(dl.delta_from_price(px, SPOT, K, T, is_call) - bs.delta(SPOT, K, T, iv, is_call)) < 1e-6
    assert dl.implied_vol(0.0, SPOT, 24000, T, True) is None  # below the no-arbitrage band
    assert dl.implied_vol(30000.0, SPOT, 24000, T, True) is None  # above it
    # floor on time: after 15:30 on the expiry day T does not go to zero
    assert dl.years_to_expiry(EXPIRY, datetime(2026, 1, 9, 15, 31)) > 0


# ---------- entry strikes and the A/B/C structure ----------
def test_entry_picks_nearest_not_above_25_delta():
    bars, book, base = make_world()
    s, out = sim("A", bars, book)
    exp = expected_entry(base)
    assert out["status"] == "traded"
    assert out["entry"]["call_strike"] == exp["CE"] and out["entry"]["put_strike"] == exp["PE"], (out["entry"], exp)
    assert 0.20 < out["entry"]["call_delta"] <= 0.25 + 1e-9 and 0.20 < out["entry"]["put_delta"] <= 0.25 + 1e-9
    # entry fills at the 09:45 open minus slippage, decided on the 09:40 close
    e = [x for x in s.events if x["kind"] == "enter"][0]
    assert e["decision_ts"] == BARS[I["09:40"]] and e["fill_ts"] == BARS[I["09:45"]]
    # fills: sold at the 09:45 open minus slippage
    assert abs(out["entry"]["call_px"] - (base[("CE", exp["CE"])] - 0.10)) < 1e-9
    assert abs(out["entry"]["put_px"] - (base[("PE", exp["PE"])] - 0.10)) < 1e-9


# ---------- 25% trigger and re-match, worked by hand ----------
def _rematch_world(**kw):
    bars, book, base = make_world()
    exp = expected_entry(base)
    kc, kp = exp["CE"], exp["PE"]
    sale_c = base[("CE", kc)] - 0.10
    sale_p = base[("PE", kp)] - 0.10
    return base, kc, kp, sale_c, sale_p


def test_25pct_trigger_and_rematch_hand_computed():
    base, kc, kp, sale_c, sale_p = _rematch_world()
    # Call mark must reach 1.25 x sale: choose a price just below, then just above, the trigger.
    trig_px = 1.25 * sale_c
    below, above = trig_px - 0.5, trig_px + 0.5
    # candidate puts: keep the generated BS prices; hand-pick the target = the risen call's mark ("above")
    changes = [("10:20", "CE", kc, below), ("10:30", "CE", kc, above)]
    bars, book, _ = make_world(changes=changes)
    s, out = sim("A", bars, book)
    adj = [e for e in s.events if e["kind"] == "adjust"]
    assert len(adj) == 1, s.events
    a = adj[0]
    # nothing at 10:20 (below the trigger); decision on the 10:30 bar close, fill at the 10:35 open
    assert a["decision_ts"] == BARS[I["10:30"]] and a["fill_ts"] == BARS[I["10:35"]]
    # hand computation of the new put: among puts at or below ATM (24000), the one whose price is nearest `above`
    cands = [(abs(base[("PE", K)] - above), -abs(K - 24000), K) for K in STRIKES if K <= 24000]
    new_k = min(cands)[2]
    assert a["new_strike"] == new_k and a["risen"] == "CE"
    assert abs(a["bought"] - (base[("PE", kp)] + 0.10)) < 1e-9  # decayed put bought back at open + slippage
    assert abs(a["sold"] - (base[("PE", new_k)] - 0.10)) < 1e-9  # new put sold at open - slippage
    # references reset: call reference = its mark (above); new put reference = its sale fill
    # (sim is finished, so check through a run that stops right after the adjustment: end of day legs are gone; recompute from events instead)
    assert s.n_adjust == 1 and out["n_adjust"] == 1
    # after matching, the new put price is close to the call price (that is the point of re-matching)
    assert abs(base[("PE", new_k)] - above) <= abs(base[("PE", kp)] - above)


def test_no_trigger_below_25pct():
    base, kc, kp, sale_c, sale_p = _rematch_world()
    bars, book, _ = make_world(changes=[("10:30", "CE", kc, 1.25 * sale_c - 0.05)])
    s, out = sim("A", bars, book)
    assert out["n_adjust"] == 0 and out["end_reason"] == "eod"


def test_references_after_adjustment():
    base, kc, kp, sale_c, sale_p = _rematch_world()
    above = 1.25 * sale_c + 0.5
    bars, book, _ = make_world(changes=[("10:30", "CE", kc, above)])
    # stop the day right after the adjustment fill by making the index run away is complicated; instead stop the clock: inspect legs via a hook
    s = bt.DaySim("A", bars, 23800.0, 24200.0, book, EXPIRY, OptionCostModel(slippage_rs=0.10), bt.Params())
    orig = s._exec_pending
    seen = {}

    def spy(j):
        was = s.pending
        orig(j)
        if was and was[0] == "adjust" and "legs" not in seen:
            seen["legs"] = {k: dict(v) for k, v in s.legs.items()}

    s._exec_pending = spy
    s.run()
    L = seen["legs"]
    assert abs(L["CE"]["ref"] - above) < 1e-9  # risen leg's reference = its mark at the decision bar
    assert abs(L["PE"]["ref"] - L["PE"]["sale"]) < 1e-9  # new leg's reference = its own sale fill


# ---------- straddle stage: 30% stop, no more 25% adjustments ----------
def _straddle_world(final_call_mult, extra=()):
    """Step 1: put explodes to 400 -> a new ATM call is sold (strike 24000). Step 2: that call rises >= 25% -> a new ATM put is sold -> straddle at 24000."""
    bars0, book0, base = make_world()
    exp = expected_entry(base)
    kp = exp["PE"]
    atm_c, atm_p = base[("CE", 24000)], base[("PE", 24000)]
    call_sale = atm_c - 0.10
    changes = [("10:00", "PE", kp, 400.0)]  # put leg explodes -> adjust at 10:00 close, fill 10:05
    changes += [("10:30", "CE", 24000, 1.30 * call_sale + 0.5)]  # new call rises >=25% -> adjust -> new ATM put (straddle)
    changes += list(extra)
    return changes, base, call_sale, atm_p


def test_straddle_stage_30pct_stop():
    changes, base, call_sale, atm_p = _straddle_world(1.0)
    bars, book, _ = make_world(changes=changes)
    s = bt.DaySim("A", bars, 23800.0, 24200.0, book, EXPIRY, OptionCostModel(slippage_rs=0.10), bt.Params())
    snap = {}
    orig = s._exec_pending

    def spy(j):
        was = s.pending
        orig(j)
        if was and was[0] == "adjust" and s.mode == "straddle" and "x" not in snap:
            snap["x"] = {k: dict(v) for k, v in s.legs.items()}

    s._exec_pending = spy
    s.run()
    assert s.n_adjust == 2, s.events
    L = snap["x"]
    assert L["CE"]["strike"] == L["PE"]["strike"] == 24000
    call_ref = 1.30 * call_sale + 0.5  # risen call's mark at the decision bar
    assert abs(L["CE"]["ref"] - call_ref) < 1e-9
    assert abs(L["CE"]["stop"] - 1.30 * call_ref) < 1e-9 and abs(L["PE"]["stop"] - 1.30 * L["PE"]["ref"]) < 1e-9
    # with a call mark above 1.25 x ref but below the 30% stop: still no further adjustment, no exit
    call_ref_stop = 1.30 * call_ref
    ch2 = changes + [("11:00", "CE", 24000, 1.27 * call_ref)]
    bars2, book2, _ = make_world(changes=ch2)
    s2, o2 = sim("A", bars2, book2)
    assert o2["n_adjust"] == 2 and o2["end_reason"] == "eod", (o2["n_adjust"], o2["end_reason"])
    # at 1.31 x ref the straddle stop fires: decision on that bar's close, everything exits at the next open
    ch3 = changes + [("11:00", "CE", 24000, 1.31 * call_ref)]
    bars3, book3, _ = make_world(changes=ch3)
    s3, o3 = sim("A", bars3, book3)
    assert o3["end_reason"] == "straddle_stop"
    ex = [e for e in s3.events if e["kind"] == "exit_leg"]
    assert len(ex) == 2 and all(e["decision_ts"] == BARS[I["11:00"]] and e["fill_ts"] == BARS[I["11:05"]] for e in ex), ex


# ---------- breakout confirmation: two consecutive 15-minute closes ----------
def test_breakout_needs_two_consecutive_15min_closes():
    # one 15-min bar (10:00-10:15) closes above 24200, then back inside: no range exit
    one = {"10:00": 24250.0, "10:15": 24000.0}
    bars, book, _ = make_world(spot_path=one)
    s, o = sim("A", bars, book)
    assert o["end_reason"] == "eod" and not [e for e in s.events if e["kind"] == "exit_leg" and e["reason"] == "range_exit"]
    # a 5-minute close above the boundary that is not a 15-minute close does not count
    mid = {"10:05": 24250.0, "10:10": 24000.0}
    bars, book, _ = make_world(spot_path=mid)
    s, o = sim("A", bars, book)
    assert o["end_reason"] == "eod"
    # two consecutive 15-min closes above (10:00-10:15 and 10:15-10:30): decide on the 10:25 bar (close 10:30), exit at the 10:30 open
    two = {"10:00": 24250.0, "10:30": 24000.0}
    bars, book, _ = make_world(spot_path=two)
    s, o = sim("A", bars, book)
    ex = [e for e in s.events if e["kind"] == "exit_leg"]
    assert o["end_reason"] == "range_exit" and len(ex) == 2
    assert all(e["decision_ts"] == BARS[I["10:25"]] and e["fill_ts"] == BARS[I["10:30"]] for e in ex), ex
    # above, then below the OTHER boundary: not consecutive beyond the same boundary
    flip = {"10:00": 24250.0, "10:15": 23750.0, "10:30": 24000.0}
    bars, book, _ = make_world(spot_path=flip)
    s, o = sim("A", bars, book)
    assert o["end_reason"] == "eod"


# ---------- A versus B ----------
def test_a_vs_b_on_a_confirmed_up_breakout():
    base, kc, kp, sale_c, sale_p = _rematch_world()
    up = {"10:00": 24250.0, "10:30": 24260.0}  # stays above 24200 for the rest of the day
    # the put keeps decaying after the breakout (mark far below its sale): B should hold it to 15:15
    decay = [("10:00", "PE", kp, 0.5 * sale_p)]
    bars, book, _ = make_world(spot_path=up, changes=decay)
    sa, oa = sim("A", bars, book)
    sb, ob = sim("B", bars, book)
    assert oa["end_reason"] == "range_exit" and oa["orders"] == 4  # 2 entry + 2 exit
    fa = {e["leg"]: e["fill_ts"] for e in sa.events if e["kind"] == "exit_leg"}
    assert fa["CE"] == fa["PE"]
    exb = [e for e in sb.events if e["kind"] == "exit_leg"]
    assert [e["leg"] for e in exb] == ["CE", "PE"]
    assert exb[0]["reason"] == "range_exit" and exb[0]["fill_ts"] == BARS[I["10:30"]]
    assert exb[1]["reason"] == "eod" and exb[1]["fill_ts"] == BARS[I["15:15"]]
    assert ob["breakout"] and ob["end_reason"] == "eod" and ob["orders"] == 4
    # B: if the held leg's mark returns to its sale price after the breakout, it exits (cost-to-cost)
    back = [("10:00", "PE", kp, 0.5 * sale_p), ("11:00", "PE", kp, sale_p + 0.05)]
    bars, book, _ = make_world(spot_path=up, changes=back)
    sb2, ob2 = sim("B", bars, book)
    ex2 = [e for e in sb2.events if e["kind"] == "exit_leg" and e["leg"] == "PE"][0]
    assert ob2["end_reason"] == "cost_to_cost" and ex2["decision_ts"] == BARS[I["11:00"]] and ex2["fill_ts"] == BARS[I["11:05"]]
    # B on a DOWN breakout buys back the put and holds the call
    down = {"10:00": 23750.0, "10:30": 23740.0}
    bars, book, _ = make_world(spot_path=down, changes=[("10:00", "CE", kc, 0.5 * sale_c)])
    sb3, ob3 = sim("B", bars, book)
    assert [e["leg"] for e in sb3.events if e["kind"] == "exit_leg"] == ["PE", "CE"]


# ---------- C: hedge and bounded loss ----------
def test_hedge_max_loss_formula():
    # shorts 24250 / 23750, wings 24450 / 23550, premium received 100 points net.
    # held to expiry only one side can be in the money: (200 - 100) x 75 = 7,500; intraday both spreads can carry value: (400 - 100) x 75 = 22,500
    assert bt.hedge_max_loss_at_expiry(24250, 23750, 24450, 23550, 100.0, 75) == 7500.0
    assert bt.hedge_max_loss(24250, 23750, 24450, 23550, 100.0, 75) == 22500.0
    assert bt.hedge_max_loss_at_expiry(24250, 23750, 24450, 23550, 250.0, 75) == 0.0  # credit above the width cannot lose at expiry


def test_c_buys_wings_and_loss_is_bounded():
    bars0, book0, base = make_world()
    exp = expected_entry(base)
    kc, kp = exp["CE"], exp["PE"]
    # violent gap up through the zone: short call and its wing explode (spread value capped at its 200-point width)
    spot_up = {"10:00": kc + 400.0, "10:30": kc + 400.0}
    short_px, wing_px = 405.0, 205.0  # intrinsic 400 + 5 time value vs 200 + 5: spread = 200
    ch = [("10:00", "CE", kc, short_px), ("10:00", "CE", kc + 200, wing_px)]
    bars, book, _ = make_world(spot_path=spot_up, changes=ch)
    s, o = sim("C", bars, book, p=bt.Params(adj_trigger=1e9))  # isolate the hedge: no adjustments
    assert o["status"] == "traded" and o["end_reason"] == "range_exit"
    # entry has 4 legs (2 shorts + 2 wings); exit closes 4 legs: 8 orders, no adjustments move the wings
    assert o["orders"] == 8 and o["n_adjust"] == 0
    # the wings sit 200 points beyond the shorts
    credit = (base[("CE", kc)] - 0.10) + (base[("PE", kp)] - 0.10) - (base[("CE", kc + 200)] + 0.10) - (base[("PE", kp - 200)] + 0.10)
    bound = bt.hedge_max_loss(kc, kp, kc + 200, kp - 200, credit, 75)
    slip_allow = 4 * 0.10 * 75  # four exit fills each worse by the slippage
    assert -o["gross"] <= bound + slip_allow + 1e-6, (o["gross"], bound)
    assert bt.hedge_max_loss_at_expiry(kc, kp, kc + 200, kp - 200, credit, 75) < bound  # the expiry-hold bound is the tighter, narrower claim
    assert o["gross"] < 0  # it was a loss day
    # the same day for A has a much bigger loss (no wings)
    sa, oa = sim("A", bars, book, p=bt.Params(adj_trigger=1e9))
    assert -oa["gross"] > -o["gross"]
    assert o["max_width_pts"] == 200.0


def test_c_skipped_when_wing_candle_missing():
    bars0, book0, base = make_world()
    exp = expected_entry(base)
    drop = {("CE", exp["CE"] + 200, "09:45")}
    bars, book, _ = make_world(drop=drop)
    s, o = sim("C", bars, book)
    assert o["status"] == "skipped" and o["reason"] == "wing_unavailable"
    sa, oa = sim("A", bars, book)
    assert oa["status"] == "traded"


# ---------- costs: every order is charged, adjustments add orders ----------
def test_cost_counts_orders_and_matches_cost_model():
    base, kc, kp, sale_c, sale_p = _rematch_world()
    bars, book, _ = make_world(changes=[("10:30", "CE", kc, 1.25 * sale_c + 0.5)])
    cm = OptionCostModel(slippage_rs=0.10)
    s = bt.DaySim("A", bars, 23800.0, 24200.0, book, EXPIRY, cm, bt.Params())
    o = s.run()
    # entry 2 sells, adjustment 1 buy + 1 sell, exit 2 buys = 6 orders; no adjustment would have been 4
    assert o["orders"] == 6 and o["n_adjust"] == 1
    sells = [sale_c, sale_p]
    adj = [e for e in s.events if e["kind"] == "adjust"][0]
    exits = [e["px"] for e in s.events if e["kind"] == "exit_leg"]
    expected_cost = (cm.side(sale_c, 75, False) + cm.side(sale_p, 75, False) + cm.side(adj["bought"], 75, True) + cm.side(adj["sold"], 75, False)
                     + sum(cm.side(x, 75, True) for x in exits))
    assert abs(o["cost"] - expected_cost) < 1e-6
    gross = 75 * (sale_c + sale_p - adj["bought"] + adj["sold"] - sum(exits))
    assert abs(o["gross"] - gross) < 1e-6 and abs(o["net"] - (gross - expected_cost)) < 1e-6
    # selling is where STT lands: buys carry none
    assert cm.side(100, 75, True) < cm.side(100, 75, False)
    # higher slippage lowers net on the same path
    o2 = bt.DaySim("A", bars, 23800.0, 24200.0, book, EXPIRY, OptionCostModel(slippage_rs=0.30), bt.Params()).run()
    assert o2["net"] < o["net"]


# ---------- missing candles ----------
def test_missing_candle_skips_adjustment_and_retries_next_bar():
    base, kc, kp, sale_c, sale_p = _rematch_world()
    above = 1.25 * sale_c + 0.5
    ch = [("10:30", "CE", kc, above)]
    bars, book, _ = make_world(changes=ch)
    s, o = sim("A", bars, book)
    new_k = [e for e in s.events if e["kind"] == "adjust"][0]["new_strike"]
    # remove the candle of the leg to be BOUGHT BACK (the old put) at the fill bar 10:35: the adjustment is skipped and counted, then done a bar later
    bars, book, _ = make_world(changes=ch, drop={("PE", kp, "10:35")})
    s2, o2 = sim("A", bars, book)
    assert o2["skipped_adjust"] == 1 and o2["n_adjust"] == 1
    a = [e for e in s2.events if e["kind"] == "adjust"][0]
    assert a["fill_ts"] == BARS[I["10:40"]] and a["decision_ts"] == BARS[I["10:35"]]
    # a missing entry candle skips the day and says why
    bars, book, base = make_world(drop={("CE", expected_entry(base)["CE"], "09:45")})
    s3, o3 = sim("A", bars, book)
    assert o3["status"] == "skipped" and o3["reason"] == "no_entry_candle"
    # the EOD exit retries bar by bar when the 15:15 candle is missing
    kcs = expected_entry(base)["CE"]
    bars, book, _ = make_world(drop={("CE", kcs, "15:15")})
    s4, o4 = sim("A", bars, book)
    e = [x for x in s4.events if x["kind"] == "exit_leg" and x["leg"] == "CE"][0]
    assert o4["skipped_exit"] == 1 and e["fill_ts"] == BARS[I["15:20"]] and o4["end_reason"] == "eod"


# ---------- no lookahead ----------
def test_no_lookahead_future_candles_do_not_change_earlier_actions():
    base, kc, kp, sale_c, sale_p = _rematch_world()
    ch = [("10:30", "CE", kc, 1.25 * sale_c + 0.5)]
    sp = {"10:00": 24050.0}
    bars, book, _ = make_world(changes=ch, spot_path=sp)
    s, o = sim("A", bars, book)
    cut = "11:00"
    # scramble EVERYTHING that starts after `cut` (index and every option), keep the past identical
    rng = np.random.default_rng(1)
    junk = [(b.strftime("%H:%M"), t, K, float(rng.uniform(1, 900))) for b in BARS if b.strftime("%H:%M") > cut for K in STRIKES[::7] for t in ("CE", "PE")]
    spj = dict(sp)
    spj.update({b.strftime("%H:%M"): float(rng.uniform(23000, 25000)) for b in BARS if b.strftime("%H:%M") > cut})
    bars2, book2, _ = make_world(changes=ch + junk, spot_path=spj)
    s2, o2 = sim("A", bars2, book2)
    cut_ts = BARS[I[cut]]
    past1 = [e for e in s.events if e["fill_ts"] is not None and e["fill_ts"] <= cut_ts]
    past2 = [e for e in s2.events if e["fill_ts"] is not None and e["fill_ts"] <= cut_ts]
    assert past1 == past2 and len(past1) == 2  # entry and the adjustment, with the same fills/prices
    # and the mark used at a decision bar never comes from a later candle
    key = (EXPIRY, kc, "CE")
    assert book.last_close(key, BARS[I["10:25"]]) != book.last_close(key, BARS[I["10:30"]])


# ---------- statistics ----------
def test_stats_known_answers():
    x = [100.0, -50.0, -200.0, 30.0, -10.0, -10.0, 60.0]
    # equity curve 100, 50, -150, -120, -130, -140, -80 -> peak 100 (after day 1), trough -150: drawdown = -250
    assert ev.max_drawdown(x) == -250.0
    assert ev.longest_losing_streak(x) == 2 and ev.longest_losing_streak([1, 1]) == 0
    # a constant series: every resample mean equals the constant, so the CI collapses onto it
    lo, hi = ev.block_bootstrap_mean_ci([7.0] * 40)
    assert lo == hi == 7.0
    # a clearly positive noisy series has a CI above zero; a zero-mean one straddles zero
    rng = np.random.default_rng(0)
    lo, hi = ev.block_bootstrap_mean_ci(rng.normal(5, 1, 200))
    assert lo > 0 and hi > lo
    lo, hi = ev.block_bootstrap_mean_ci(rng.normal(0, 10, 200))
    assert lo < 0 < hi
    # deterministic given the seed
    assert ev.block_bootstrap_mean_ci(x * 5) == ev.block_bootstrap_mean_ci(x * 5)


def test_pass_rule_and_dte_buckets_and_summary_on_synthetic_day():
    bars, book, base = make_world()
    inputs = [dict(day=DAY, bars=bars, expiry=EXPIRY, zone=(23800.0, 24200.0), why=None),
              dict(day=date(2026, 1, 6), bars=bars, expiry=EXPIRY, zone=None, why="no_swing_range")]
    rows = ev.run_variant("A", 0.20, inputs, book, {})
    assert rows[0]["status"] == "traded" and rows[0]["dte"] == 4 and rows[1]["status"] == "no_signal"
    s = ev.summarize(rows, 120000.0)
    assert s["traded"] == 1 and s["no_signal"] == {"no_swing_range": 1} and s["end_reasons"] == {"eod": 1.0}
    assert s["max_dd"] == min(rows[0]["net"], 0.0) and abs(s["monthly_pct"] - rows[0]["net"] / 120000.0 * 100) < 1e-9
    t = ev.dte_table(rows)
    assert t["3-4"]["days"] == 1 and t["0"]["days"] == 0 and abs(t["3-4"]["total"] - rows[0]["net"]) < 1e-9
    good = {"traded": 40, "mean": 10.0, "mean_ci95": (1.0, 19.0), "total": 400.0, "worst": -100.0, "capital": 120000.0}
    res = {0.20: good, 0.30: dict(good, mean=1.0)}
    assert ev.pass_rule(res)["useful"]
    assert not ev.pass_rule({0.20: dict(good, mean_ci95=(-1.0, 19.0)), 0.30: good})["useful"]  # CI includes zero
    assert not ev.pass_rule({0.20: dict(good, total=250.0), 0.30: good})["useful"]  # total < 3 x worst day
    assert not ev.pass_rule({0.20: good, 0.30: dict(good, mean=-1.0)})["useful"]  # fails at Rs0.30
    assert not ev.pass_rule({0.20: dict(good, worst=-7000.0, total=99999.0), 0.30: good})["useful"]  # worst day >= 5% of capital (6,000)


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as e:  # noqa: BLE001
            import traceback
            fails += 1
            print("FAIL", name, repr(e)[:400])
            traceback.print_exc(limit=3)
    print(f"{len(tests) - fails}/{len(tests)} passed")
    sys.exit(1 if fails else 0)
