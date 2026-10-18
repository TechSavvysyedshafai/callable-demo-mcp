"""Task 7 (settlement mechanics) self-checks: hand-computed payoffs and fees, the Asian 1/sqrt(3) arithmetic, no lookahead (only candles at or
before 15:00 decide; settlement comes from the official daily close), skipped-day accounting, G0, T3 pin logic, verdict rules, ledger.
Run:  python research/settlement/tests/test_settlement.py   (also collected by pytest)."""

import math
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import settlement_core as sc  # noqa: E402
from costs_opt import OptionCostModel  # noqa: E402

EX = date(2026, 1, 8)


def approx(a, b, tol=1e-6):
    assert abs(a - b) <= tol, (a, b)


# ---------------------------------------------------------------------------------------------- synthetic world
def make_bars(day=EX, s0=24012.0, a_last=24100.0, drift_before=0.0, extra_after=None):
    """One day of 75 five-minute bars; bar 15:00 opens at s0, bar 15:25 closes at a_last. Earlier bars wiggle by +/-5."""
    t0 = datetime.combine(day, time(9, 15))
    ts = [t0 + timedelta(minutes=5 * i) for i in range(75)]
    rows = []
    px = s0 - 30 + drift_before
    for i, t in enumerate(ts):
        o = px
        c = s0 if t.time() == time(14, 55) else px + (5 if i % 2 == 0 else -5)
        if t.time() == time(15, 0):
            o = s0
        if t.time() == time(15, 25):
            c = a_last
        h, l = max(o, c) + 1, min(o, c) - 1
        rows.append({"date": t, "open": o, "high": h, "low": l, "close": c, "volume": 0})
        px = c
    df = pd.DataFrame(rows)
    if extra_after is not None:  # scramble everything from 15:05 on (opens/closes) to prove nothing there is used for a decision
        m = df["date"].dt.time >= time(15, 5)
        df.loc[m, ["open", "close"]] = extra_after
    return df


def make_leg(day, opens_by_time: dict, oi_by_time: dict | None = None, default=50.0):
    """Option candles for one expiry day; `opens_by_time` overrides the open at given times; every 5-minute bar exists unless value is None."""
    t0 = datetime.combine(day, time(9, 15))
    rows = []
    for i in range(75):
        t = t0 + timedelta(minutes=5 * i)
        o = opens_by_time.get(t.time(), default)
        if o is None:
            continue
        rows.append({"date": t, "open": o, "high": o, "low": o, "close": o, "volume": 1, "oi": (oi_by_time or {}).get(t.time(), 1000.0)})
    return pd.DataFrame(rows).set_index("date")


class World:
    """Monkeypatches settlement_core.load_leg so tests need no files."""

    def __init__(self, legs: dict):
        self.legs = legs

    def __enter__(self):
        self.old = sc.load_leg
        sc.load_leg = lambda ex, k, kind: self.legs.get((ex, k, kind))
        return self

    def __exit__(self, *a):
        sc.load_leg = self.old


# ---------------------------------------------------------------------------------------------- arithmetic
def test_strike_rounding_half_up():
    assert sc.round_strike(24024.9) == 24000
    assert sc.round_strike(24025.0) == 24050  # half rounds UP (round() would give 24000)
    assert sc.round_strike(24075.0) == 24100
    assert sc.round_strike(24012.0) == 24000 and sc.round_strike(24040.0) == 24050


def test_straddle_payoff_signs_known_answers():
    defs = sc.leg_defs(24000, wings=False)
    opens = {"sc": 100.0, "sp": 90.0}
    for settle, want in [(24000, 190), (24150, 40), (23850, 40), (24190, 0), (24300, -110), (23700, -110)]:  # points per unit
        r = sc.price_trade(opens, defs, settle, 0.0, None, fees=False)
        approx(r["pts"], want)
        approx(r["gross_rs"], want * 75)
    # wings K+/-100 bought at 60 and 55: credit 190 - 115 = 75; loss is capped at width - credit = 25 on both sides
    d2 = sc.leg_defs(24000, wings=True)
    assert d2["lc"] == (24100, "CE", True) and d2["lp"] == (23900, "PE", True) and d2["sc"][2] is False
    o2 = {"sc": 100.0, "sp": 90.0, "lc": 60.0, "lp": 55.0}
    for settle, want in [(24000, 75), (24050, 25), (24100, -25), (24500, -25), (23900, -25), (23500, -25), (24200, -25)]:
        approx(sc.price_trade(o2, d2, settle, 0.0, None, fees=False)["pts"], want)
    sweep = [sc.price_trade(o2, d2, s, 0.0, None, fees=False)["pts"] for s in range(22000, 26001, 5)]
    approx(max(sweep), 75)
    approx(min(sweep), -25)


def test_slippage_hurts_both_sides():
    defs = sc.leg_defs(24000, wings=True)
    o = {"sc": 100.0, "sp": 90.0, "lc": 60.0, "lp": 55.0}
    base = sc.price_trade(o, defs, 24000, 0.0, None, fees=False)["pts"]  # 75
    slipped = sc.price_trade(o, defs, 24000, 0.20, None, fees=False)["pts"]
    approx(slipped, 75 - 4 * 0.20)  # 2 sells fill 0.20 lower, 2 buys fill 0.20 higher
    straddle = sc.price_trade({"sc": 100.0, "sp": 90.0}, sc.leg_defs(24000, False), 24000, 0.20, None, fees=False)["pts"]
    approx(straddle, 190 - 2 * 0.20)
    assert base - slipped > 0


def test_fee_arithmetic_by_hand():
    # one SELL of premium 100, 75 units: turnover 7,500
    cm = OptionCostModel(slippage_rs=0.0)
    exch, sebi = 0.0003553 * 7500, 0.000001 * 7500
    want_side = 20 + exch + sebi + 0.18 * (20 + exch + sebi) + 0.0015 * 7500
    approx(want_side, 38.003255, 1e-6)
    approx(cm.side(100.0, 75, is_buy=False), want_side)
    defs = sc.leg_defs(24000, False)
    r = sc.price_trade({"sc": 100.0, "sp": 100.0}, defs, 24150, 0.0, cm)
    approx(r["entry_fees"], 2 * want_side)  # two sell orders, brokerage Rs20 each
    approx(r["settle_stt"], 0.0015 * 150 * 75)  # only the call is in the money: 16.875
    approx(r["pts"], 200 - 150)
    approx(r["net_rs"], 50 * 75 - 2 * want_side - 16.875)  # 3657.118490
    approx(r["net_rs"], 3657.11849, 1e-5)
    # a BUY pays stamp, no STT: premium 60
    t = 60.0 * 75
    e2, s2 = 0.0003553 * t, 0.000001 * t
    approx(cm.side(60.0, 75, is_buy=True), 20 + e2 + s2 + 0.18 * (20 + e2 + s2) + 0.00003 * t)
    # wings: 4 orders -> 4 x Rs20 brokerage; settlement STT on every in-the-money leg (short and long)
    d2 = sc.leg_defs(24000, True)
    r2 = sc.price_trade({"sc": 100.0, "sp": 90.0, "lc": 60.0, "lp": 55.0}, d2, 24500, 0.0, cm)
    approx(r2["settle_stt"], 0.0015 * (500 + 400) * 75)  # short call 500 + long call 400
    assert r2["entry_fees"] > 4 * 20


def test_asian_one_over_root_three():
    approx(1 / math.sqrt(3), 0.5773502692, 1e-9)
    approx(sc.model_asian_straddle(10.0), 10 * math.sqrt(6) / math.sqrt(3))  # = 10 * sqrt(2)
    approx(sc.model_asian_straddle(10.0), 14.142135623, 1e-8)
    approx(sc.model_asian_straddle(10.0, normal_factor=True), 14.142135623 * math.sqrt(2 / math.pi), 1e-8)
    approx(0.58 * 10 * math.sqrt(6), 14.2, 0.3)  # the brief's rounded 0.58 is within 0.4% of the exact factor
    # closed form for a discrete average of n steps: ratio = sqrt((n+1)(2n+1)/(6 n^2)) -> 1/sqrt(3)
    n = 6
    approx(math.sqrt((n + 1) * (2 * n + 1) / (6 * n * n)), math.sqrt(91 / 216))
    big = 1_000_000
    approx(math.sqrt((big + 1) * (2 * big + 1) / (6 * big * big)), 1 / math.sqrt(3), 1e-6)
    # simulation: the std of the average of a random walk over [0,T] versus the std of its endpoint
    rng = np.random.default_rng(1)
    steps = rng.standard_normal((20000, 600))
    paths = steps.cumsum(axis=1)
    ratio = paths.mean(axis=1).std() / paths[:, -1].std()
    assert abs(ratio - 1 / math.sqrt(3)) < 0.02, ratio


# ---------------------------------------------------------------------------------------------- G0
def test_g0_known_ratio_and_stop():
    frames = []
    closes = {}
    exps = []
    for i, (a_minus, s1_minus) in enumerate([(0, 0), (10, 20), (20, 40)]):
        d = date(2026, 1, 8) + timedelta(days=7 * i)
        exps.append(d)
        frames.append(make_bars(d, s0=24000.0, a_last=24000.0 + s1_minus))
        closes[d] = 24000.0 + a_minus
    bars = pd.concat(frames, ignore_index=True)
    g = sc.gate_g0(bars, closes, exps)
    assert g["n"] == 3 and not g["skipped"]
    approx(g["std_A_minus_S0"], 10.0)  # std of [0,10,20], ddof 1
    approx(g["std_S1_minus_S0"], 20.0)
    approx(g["ratio"], 0.5)
    assert g["stop"] is False
    closes2 = {d: 24000.0 + x for d, x in zip(exps, (0, 20, 40))}  # official close = last print -> ratio 1.0 -> STOP
    g2 = sc.gate_g0(bars, closes2, exps)
    approx(g2["ratio"], 1.0)
    assert g2["stop"] is True
    closes3 = {d: 24000.0 + x for d, x in zip(exps, (0, 17, 34))}  # 0.85 exactly is NOT above the limit
    approx(sc.gate_g0(bars, closes3, exps)["ratio"], 0.85)
    assert sc.gate_g0(bars, closes3, exps)["stop"] is False


# ---------------------------------------------------------------------------------------------- trial runs, lookahead, skips
def full_world(day=EX, s0=24012.0, a=24100.0):
    k = sc.round_strike(s0)
    legs = {(day, k, "CE"): make_leg(day, {time(15, 0): 100.0}), (day, k, "PE"): make_leg(day, {time(15, 0): 90.0}),
            (day, k + 100, "CE"): make_leg(day, {time(15, 0): 60.0}), (day, k - 100, "PE"): make_leg(day, {time(15, 0): 55.0})}
    return k, legs


def test_trial_uses_1500_open_and_official_close():
    k, legs = full_world()
    bars = make_bars(EX, s0=24012.0, a_last=24060.0)  # last print 24060 ...
    closes = {EX: 24100.0}  # ... but the official close (average) is 24100: the payoff must use 24100
    with World(legs):
        r = sc.run_straddle_trial(bars, closes, [EX], wings=False)
    assert len(r["rows"]) == 1 and not r["skipped"]
    row = r["rows"][0]
    assert row["K"] == 24000 and row["S0"] == 24012.0 and row["A"] == 24100.0 and row["S1"] == 24060.0
    approx(row["gross_mid_rs"], (190 - 100) * 75)  # call intrinsic 100 against A=24100 (would be 60 against the last print)
    sl = 0.20
    fees = 2 * OptionCostModel(slippage_rs=sl).side(100.0 - sl, 75, False) * 0 + OptionCostModel().side(100.0 - sl, 75, False) + OptionCostModel().side(90.0 - sl, 75, False)
    approx(row["net_0.20"], (190 - 2 * sl - 100) * 75 - fees - 0.0015 * 100 * 75)


def test_no_lookahead_after_1500():
    k, legs = full_world()
    bars = make_bars(EX, s0=24012.0, a_last=24060.0)
    scrambled_bars = make_bars(EX, s0=24012.0, a_last=24060.0, extra_after=19999.0)
    scrambled_bars.loc[scrambled_bars["date"].dt.time == time(15, 25), "close"] = 24060.0  # S1 itself is only reported, not traded
    legs2 = {}
    for key, df in legs.items():  # scramble every option candle after 15:00 (open/close/OI): the trade must not move
        d = df.copy()
        late = d.index.time > time(15, 0)
        d.loc[late, ["open", "close", "oi"]] = 7777.0
        legs2[key] = d
    closes = {EX: 24100.0}
    with World(legs):
        a = sc.run_straddle_trial(bars, closes, [EX], wings=True)["rows"][0]
    with World(legs2):
        b = sc.run_straddle_trial(scrambled_bars, closes, [EX], wings=True)["rows"][0]
    for key in ("net_0.10", "net_0.20", "net_0.30", "gross_mid_rs", "straddle_px", "K", "sigma_pts"):
        approx(a[key], b[key])
    # but the 15:00 candle IS the decision price: changing it changes the trade
    legs3 = {key: df.copy() for key, df in legs.items()}
    legs3[(EX, k, "CE")].loc[datetime.combine(EX, time(15, 0)), "open"] = 120.0
    with World(legs3):
        c = sc.run_straddle_trial(bars, closes, [EX], wings=True)["rows"][0]
    assert abs(c["net_0.20"] - a["net_0.20"]) > 100


def test_sigma_uses_only_bars_before_1500():
    f1 = sc.day_frame(make_bars(EX), EX)
    f2 = sc.day_frame(make_bars(EX, extra_after=30000.0), EX)
    approx(sc.sigma_points(f1), sc.sigma_points(f2))
    assert sc.sigma_points(f1) > 0


def test_skipped_day_accounting():
    days = [date(2026, 1, 8) + timedelta(days=7 * i) for i in range(5)]
    bars = pd.concat([make_bars(d, s0=24012.0, a_last=24050.0) for d in days], ignore_index=True)
    closes = {d: 24100.0 for d in days}
    del closes[days[4]]  # no official close on the last day
    k = 24000
    legs = {}
    for d in (days[0], days[2], days[3], days[4]):  # day 1 has NO files at all
        legs[(d, k, "CE")] = make_leg(d, {time(15, 0): 100.0})
        legs[(d, k, "PE")] = make_leg(d, {time(15, 0): 90.0})
        legs[(d, k + 100, "CE")] = make_leg(d, {time(15, 0): 60.0})
        legs[(d, k - 100, "PE")] = make_leg(d, {time(15, 0): 55.0})
    legs[(days[2], k, "PE")] = make_leg(days[2], {time(15, 0): None})  # day 2: the put has no 15:00 candle
    legs[(days[3], k - 100, "PE")] = make_leg(days[3], {time(15, 0): 0.0})  # day 3: wing open is 0 -> unusable for T2 only
    with World(legs):
        t1 = sc.run_straddle_trial(bars, closes, days, wings=False)
        t2 = sc.run_straddle_trial(bars, closes, days, wings=True)
    reasons1 = dict((d, r) for d, r in t1["skipped"])
    assert reasons1 == {days[1]: "missing_option_file", days[2]: "missing_candle_at_1500", days[4]: "no_daily_close"}
    assert [r["expiry"] for r in t1["rows"]] == [days[0], days[3]]
    reasons2 = dict((d, r) for d, r in t2["skipped"])
    assert reasons2[days[3]] == "missing_candle_at_1500" and len(t2["rows"]) == 1
    for t in (t1, t2):
        assert len(t["rows"]) + len(t["skipped"]) == len(days)  # every expiry is either traded or listed as skipped


# ---------------------------------------------------------------------------------------------- statistics
def test_halves_verdict_and_bootstrap():
    d = [date(2025, 1, 1) + timedelta(days=10 * i) for i in range(10)]
    net = np.array([5.0] * 5 + [-1.0] * 5)
    h = sc.halves_means(d, net)
    assert h["first_n"] == 5 and h["second_n"] == 5 and h["first_mean"] == 5.0 and h["second_mean"] == -1.0
    v, ch = sc.verdict(1.0, 0.001, 80, 2.0, 3.0, 40, 40)
    assert v == "SURVIVES"
    assert sc.verdict(1.0, 0.001, 59, 2.0, 3.0, 30, 29)[0] == "INCONCLUSIVE"  # too few trades
    assert sc.verdict(1.0, 0.001, 80, 2.0, -3.0, 40, 40)[0] == "INCONCLUSIVE"  # one half negative
    assert sc.verdict(1.0, 0.0039, 80, 2.0, 3.0, 40, 40)[0] == "REJECT"  # p above 0.05/13 = 0.003846
    assert sc.verdict(-1.0, 0.0001, 80, 2.0, 3.0, 40, 40)[0] == "REJECT"
    approx(sc.ALPHA, 0.05 / 13, 1e-12)
    assert abs(sc.ALPHA - 0.00385) < 1e-5
    x = np.full(80, 10.0) + np.random.default_rng(3).standard_normal(80)
    assert sc.fi.bootstrap_p(x) < 0.001
    assert sc.fi.bootstrap_p(-x) > 0.99


def test_summarise_runs_end_to_end_on_synthetic_rows():
    rows = []
    for i in range(70):
        d = date(2025, 1, 1) + timedelta(days=7 * i)
        v = 50.0 + (i % 3)
        rows.append({"expiry": d, "S0": 24000.0, "K": 24000, "A": 24000.0, "S1": 24000.0, "straddle_px": 190.0, "sigma_pts": 10.0,
                     "gross_mid_rs": v + 20, "net_0.10": v + 1, "net_0.20": v, "net_0.30": v - 1, "fees_0.10": 1, "fees_0.20": 1, "fees_0.30": 1})
    s = sc.summarise_trial(rows, [], 70)
    assert s["n"] == 70 and s["verdict"] == "SURVIVES"
    assert s["worst_trade"] == 50.0 and s["max_drawdown"] == 0.0
    approx(s["calibration"]["ratio_literal"], 190.0 / (10 * math.sqrt(2)))


# ---------------------------------------------------------------------------------------------- T3
def oi_world(day, s0, spec: dict, late: dict | None = None):
    """spec: strike -> (call OI, put OI) valid at 14:50; late: strike -> (ce, pe) written ONLY to the 14:55 and later bars (must be ignored)."""
    legs = {}
    for k, (ce, pe) in spec.items():
        for kind, v in (("CE", ce), ("PE", pe)):
            if v is None:
                continue
            oi = {time(h, m): v for h in range(9, 15) for m in range(0, 60, 5) if (h, m) >= (9, 15) and (h, m) <= (14, 50)}
            if late and k in late:
                lv = late[k][0 if kind == "CE" else 1]
                oi.update({time(14, 55): lv, time(15, 0): lv, time(15, 5): lv})
            legs[(day, k, kind)] = make_leg(day, {}, oi)
    return legs


def test_pin_day_picks_max_total_oi_from_complete_pairs_before_1450():
    spec = {24000: (100.0, 100.0), 24050: (150.0, 120.0), 24100: (500.0, None), 24150: (40.0, 60.0), 24200: (10.0, 10.0)}
    late = {24200: (9999.0, 9999.0)}  # a huge OI that appears only from the 14:55 bar: lookahead if used
    with World(oi_world(EX, 24020.0, spec, late)):
        d, why = sc.pin_day(EX, 24020.0, 24060.0)
    assert why is None
    assert d["K0"] == 24000 and d["strikes"] == [24000, 24050, 24150, 24200]  # 24100 has no put OI -> excluded
    assert d["K_max_oi"] == 24050  # 270 beats 200, 100, 20
    approx(d["dist_max"], 10.0)
    approx(d["dist_spot_strike"], 60.0)
    assert list(d["dists"]) == [60.0, 10.0, 90.0, 140.0]


def test_pin_tie_goes_to_lowest_strike_and_min_pairs():
    spec = {24000: (100.0, 100.0), 24050: (100.0, 100.0), 24100: (1.0, 1.0)}
    with World(oi_world(EX, 24020.0, spec)):
        d, _ = sc.pin_day(EX, 24020.0, 24060.0)
    assert d["K_max_oi"] == 24000 and d["tie"] is True
    with World(oi_world(EX, 24020.0, {24000: (1.0, 1.0), 24050: (2.0, 2.0)})):
        d2, why = sc.pin_day(EX, 24020.0, 24060.0)
    assert d2 is None and why == "fewer_than_3_complete_strike_pairs"


def test_pin_p_value_extremes():
    # max-OI strike sits exactly on the settlement every day among 21 strikes: observed distance 0, never beaten
    days = [{"dist_max": 0.0, "dists": np.abs(np.arange(-10, 11) * 50.0)} for _ in range(10)]
    r = sc.pin_p_value(days, n_draw=2000)
    approx(r["p"], 1 / 2001)
    assert r["obs_mean_dist"] == 0.0 and r["n"] == 10
    approx(r["expected_random_dist"], np.abs(np.arange(-10, 11) * 50.0).mean())
    # max-OI strike always the farthest strike: p = 1
    far = [{"dist_max": 500.0, "dists": np.abs(np.arange(-10, 11) * 50.0)} for _ in range(10)]
    approx(sc.pin_p_value(far, n_draw=2000)["p"], 1.0)
    # max-OI strike is a random one: p is about uniform, certainly not tiny
    rng = np.random.default_rng(5)
    rnd = []
    for _ in range(40):
        dd = np.abs(rng.integers(-10, 11) * 50.0 + np.arange(-10, 11) * 50.0)
        rnd.append({"dist_max": float(dd[rng.integers(0, 21)]), "dists": dd})
    assert sc.pin_p_value(rnd, n_draw=4000)["p"] > 0.02
    assert sc.pin_p_value([], n_draw=10)["p"] == 1.0


# ---------------------------------------------------------------------------------------------- housekeeping
def test_window_and_alpha_constants():
    assert sc.DEV_CUTOFF == date(2026, 4, 16) and sc.FIRST_EXPIRY == date(2024, 10, 3)
    assert sc.LOT == 75 and sc.WING == 100 and sc.SLIPS == (0.10, 0.20, 0.30) and sc.DECISION_SLIP == 0.20
    assert sc.T_DECISION == time(15, 0) and sc.T_OI == time(14, 50) and sc.N_DRAW == 10_000 and sc.GATE_MAX_RATIO == 0.85


def test_real_dev_expiry_list_if_present():
    try:
        bars, closes, ex = sc.load_index()
    except FileNotFoundError:
        return
    assert ex == sorted(ex) and all(sc.FIRST_EXPIRY <= e <= sc.DEV_CUTOFF for e in ex) and len(ex) == 81
    assert bars["date"].max() <= pd.Timestamp("2026-04-17")  # no holdout rows in the dev file


def test_no_code_opens_the_holdout_or_places_orders():
    for f in HERE.glob("*.py"):
        src = f.read_text()
        assert "nifty_holdout" not in src and "load_holdout" not in src, f
        assert not re.search(r"place_order|/order/place|orders/place|v2/order", src), f
        assert not re.search(r"print\([^)]*TOKEN|open\([^)]*TOKEN", src), f  # the token is never printed or written


def test_ledger_has_the_three_batch3_trials():
    sys.path.insert(0, str(HERE.parent / "ideas" / "loop"))
    import trial_ledger as tl
    n = tl.verify()
    ids = {e["idea_id"] for e in tl.events("trial")}
    if "B3-01" in ids:  # only after the run has been recorded
        assert {"B3-01", "B3-02", "B3-03"} <= ids and tl.total_trials() >= 13 and n >= 23


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"{len(fns)} tests passed")
