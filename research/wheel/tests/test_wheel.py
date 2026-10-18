"""Task 8 (wheel) self-checks: hand-computed state-machine paths (assigned, called away, stays CASH, stays LONG), payoff signs, exposure marks at official closes,
costs, no lookahead, skipped-week accounting, benchmark arithmetic, controls, statistics, ledger recording. No market data files needed.
Run:  python research/wheel/tests/test_wheel.py   (also collected by pytest)."""

import re
import sys
import tempfile
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import wheel_core as wc  # noqa: E402

Q = 75


def approx(a, b, tol=1e-6):
    assert abs(a - b) <= tol, (a, b)


def side_sell(prem):
    """Hand-derived fee of one SELL order (Rs20 brokerage, exchange 0.03553%, SEBI 0.0001%, GST 18% on those, STT 0.15% of sell premium)."""
    t = prem * Q
    ex, se = 0.0003553 * t, 0.000001 * t
    return 20 + ex + se + 0.18 * (20 + ex + se) + 0.0015 * t


def leg(ts, open_, extra=None):
    """Option candles: one candle at the entry timestamp `ts` with the given open (plus optional later candles)."""
    rows = [{"date": ts, "open": open_, "high": open_, "low": open_, "close": open_}]
    for t, o in (extra or {}).items():
        rows.append({"date": t, "open": o, "high": o, "low": o, "close": o})
    return pd.DataFrame(rows).set_index("date")


# a 5-week world (Thursdays), strikes derived from the entry spots with the repo rule
EXP = [date(2026, 1, 8) + timedelta(days=7 * i) for i in range(5)]
ENTRY_DAYS = [date(2026, 1, 1), date(2026, 1, 9), date(2026, 1, 16), date(2026, 1, 23), date(2026, 1, 30)]
SPOTS = [24000.0, 23700.0, 23800.0, 24250.0, 24300.0]
SETTLES = [23650.0, 23800.0, 24250.0, 24300.0, 23990.0]
PUTS = [23700, 23400, 23500, 23950, 24000]   # floor(spot*0.988/50)*50
CALLS = [24300, 24000, 24100, 24550, 24600]   # ceil(spot*1.012/50)*50
OPENS = {"PE": [60.0, 55.0, 50.0, 40.0, 45.0], "CE": [70.0, 30.0, 25.0, 35.0, 20.0]}


def make_plans(spots=SPOTS):
    plans = []
    for k in range(5):
        call, put = wc.short_strikes(spots[k])
        plans.append({"k": k, "expiry": EXP[k], "entry_day": ENTRY_DAYS[k], "ts": datetime.combine(ENTRY_DAYS[k], time(9, 30)),
                      "spot": spots[k], "put_k": put, "call_k": call})
    return plans


def make_loader(plans, opens=OPENS, drop=()):
    legs = {}
    for p in plans:
        for kind, strike in (("PE", p["put_k"]), ("CE", p["call_k"])):
            if (p["k"], kind) not in drop:
                legs[(p["expiry"], strike, kind)] = leg(p["ts"], opens[kind][p["k"]])
    return lambda ex, k, kind: legs.get((ex, k, kind))


CLOSES = dict(zip(EXP, SETTLES))


def test_strike_rules():
    assert wc.short_strikes(24000.0) == (24300, 23700)  # 24288 up to 24300 ; 23712 down to 23700
    assert wc.short_strikes(25000.0) == (25300, 24700)  # exact multiples stay
    assert wc.short_strikes(24500.0) == (24800, 24200)
    for k in range(5):
        call, put = wc.short_strikes(SPOTS[k])
        assert (put, call) == (PUTS[k], CALLS[k]), (k, put, call)


# ------------------------------------------------------------------------------------------------ hand-computed state-machine path
def test_wheel_path_assigned_stays_long_called_away_stays_cash_assigned():
    plans = make_plans()
    rows = wc.run_weeks(plans, CLOSES, make_loader(plans), 0.20, "wheel")
    assert [r["state_start"] for r in rows] == ["CASH", "LONG", "LONG", "CASH", "CASH"]
    assert [r["event"] for r in rows] == ["assigned", None, "called_away", None, "assigned"]
    assert [r["state_end"] for r in rows] == ["LONG", "LONG", "CASH", "CASH", "LONG"]
    assert [r["kind"] for r in rows] == ["PE", "CE", "CE", "PE", "PE"]
    assert [r["strike"] for r in rows] == [23700, 24000, 24100, 23950, 24000]
    # week 0: sell put 23700 at 60-0.2; settle 23650 -> assigned, pays 50 pts intrinsic; assignment cost on the strike notional
    f0 = 59.8
    exp0 = f0 * Q - side_sell(f0) - 50 * Q - 0.0015 * 50 * Q - 0.00065 * 23700 * Q
    approx(rows[0]["net_rs"], exp0)
    # week 1: LONG, call 24000 sold at 30-0.2; settle 23800 < strike: keeps premium; exposure mark (23800-23650)*75
    f1 = 29.8
    approx(rows[1]["net_rs"], f1 * Q - side_sell(f1) + 150 * Q)
    assert rows[1]["intrinsic_rs"] == 0 and rows[1]["expo_cost_rs"] == 0
    # week 2: LONG, call 24100 sold at 25-0.2; settle 24250 > 24100 -> called away: pays 150 intrinsic, mark (24250-23800)*75, sale cost on the strike
    f2 = 24.8
    approx(rows[2]["net_rs"], f2 * Q - side_sell(f2) - 150 * Q - 0.0015 * 150 * Q + 450 * Q - 0.00065 * 24100 * Q)
    approx(rows[2]["exposure_mark_rs"] - rows[2]["intrinsic_rs"], (24100 - 23800) * Q)  # exposure sold AT the call strike: gain capped
    # week 3: CASH, put 23950 at 40-0.2; settle 24300 > strike: stays CASH, keeps premium
    f3 = 39.8
    approx(rows[3]["net_rs"], f3 * Q - side_sell(f3))
    # week 4 (last): CASH, put 24000 at 45-0.2; settle 23990 < 24000 -> assigned (10 pts) and the open exposure is liquidated at the last close
    f4 = 44.8
    approx(rows[4]["net_rs"], f4 * Q - side_sell(f4) - 10 * Q - 0.0015 * 10 * Q - 0.00065 * 24000 * Q - 0.00065 * 23990 * Q)
    s = wc.summarise(rows, 24000 * Q)
    assert (s["assignments"], s["called_away"], s["weeks_start_cash"], s["weeks_start_long"]) == (2, 1, 3, 2)
    approx(s["wheel"]["total"], sum(r["net_rs"] for r in rows))


def test_settle_exactly_at_the_strike_does_nothing():
    plans = make_plans()
    closes = dict(CLOSES)
    closes[EXP[0]] = 23700.0  # equals the put strike
    rows = wc.run_weeks(plans, closes, make_loader(plans), 0.20, "wheel")
    assert rows[0]["event"] is None and rows[0]["state_end"] == "CASH" and rows[0]["intrinsic_rs"] == 0 and rows[0]["stt_rs"] == 0
    closes = dict(CLOSES)
    closes[EXP[1]] = 24000.0  # equals the call strike in LONG week 1
    rows = wc.run_weeks(plans, closes, make_loader(plans), 0.20, "wheel")
    assert rows[1]["event"] is None and rows[1]["state_end"] == "LONG" and rows[1]["intrinsic_rs"] == 0


def test_payoff_signs_put_and_call():
    plans = make_plans()
    prem_put = (60.0 - 0.2) * Q
    for settle, want_intr in [(24500, 0), (23701, 0), (23700, 0), (23699, 75), (23000, 700 * 75)]:
        closes = dict(CLOSES)
        closes[EXP[0]] = float(settle)
        r = wc.run_weeks(plans, closes, make_loader(plans), 0.20, "put_only")[0]
        approx(r["intrinsic_rs"], want_intr)
        approx(r["premium_rs"] - r["intrinsic_rs"], prem_put - want_intr)  # short put: gains the premium, loses below the strike
        assert r["net_rs"] <= r["premium_rs"] - r["fees_rs"] + 1e-9
    # short call: loses above the strike
    for settle, want_intr in [(23000, 0), (24000, 0), (24001, 75), (25000, 1000 * 75)]:
        closes = dict(CLOSES)
        closes[EXP[1]] = float(settle)
        r = wc.run_weeks(plans, closes, make_loader(plans), 0.20, "call_only")[1]
        approx(r["intrinsic_rs"], want_intr)
    # sweep: wheel CASH week is concave-kinked at the strike and never exceeds premium - fees
    nets = []
    for s in range(23000, 24500, 25):
        closes = dict(CLOSES)
        closes[EXP[0]] = float(s)
        rr = wc.run_weeks(plans, closes, make_loader(plans), 0.20, "put_only")[0]
        nets.append(rr["net_rs"])
    assert max(nets) == nets[-1] and nets[0] < nets[-1] and all(b >= a - 1e-9 for a, b in zip(nets, nets[1:]))


# ------------------------------------------------------------------------------------------------ exposure marking and costs
def test_exposure_is_marked_at_official_closes():
    plans = make_plans()
    rows = wc.run_weeks(plans, CLOSES, make_loader(plans), 0.20, "wheel")
    approx(rows[0]["exposure_mark_rs"], 0.0)  # CASH start: no exposure
    approx(rows[1]["exposure_mark_rs"], (23800 - 23650) * Q)
    approx(rows[2]["exposure_mark_rs"], (24250 - 23800) * Q)
    approx(rows[3]["exposure_mark_rs"], 0.0)
    # call_only (always LONG from the first entry spot): marks chain from the entry spot through every official close
    ro = wc.run_weeks(plans, CLOSES, make_loader(plans), 0.20, "call_only")
    approx(ro[0]["exposure_mark_rs"], (23650 - 24000) * Q)
    approx(sum(r["exposure_mark_rs"] for r in ro), (23990 - 24000) * Q)  # telescopes to last close - first entry spot


def test_costs_option_fees_expo_costs_and_stt():
    plans = make_plans()
    for slip in (0.10, 0.20, 0.30):
        rows = wc.run_weeks(plans, CLOSES, make_loader(plans), slip, "wheel")
        f = OPEN_PUT0 - slip
        approx(rows[0]["fees_rs"], side_sell(f))  # brokerage + exchange + SEBI + GST + STT on the sell premium
        approx(rows[0]["premium_rs"], f * Q)
        approx(rows[0]["stt_rs"], 0.0015 * 50 * Q)  # settlement STT on the in-the-money intrinsic only
        approx(rows[1]["stt_rs"], 0.0)  # out-of-the-money: no settlement STT
    rows = wc.run_weeks(plans, CLOSES, make_loader(plans), 0.20, "wheel")
    approx(rows[0]["expo_cost_rs"], 0.00065 * 23700 * Q)
    approx(rows[2]["expo_cost_rs"], 0.00065 * 24100 * Q)
    approx(rows[4]["expo_cost_rs"], 0.00065 * 24000 * Q + 0.00065 * 23990 * Q)  # assignment + liquidation of the open exposure at the end
    approx(rows[1]["expo_cost_rs"] + rows[3]["expo_cost_rs"], 0.0)
    assert all(r["fees_rs"] > 0 for r in rows)


OPEN_PUT0 = OPENS["PE"][0]


def test_slippage_changes_fills_not_the_path():
    plans = make_plans()
    paths = []
    for slip in (0.10, 0.20, 0.30):
        rows = wc.run_weeks(plans, CLOSES, make_loader(plans), slip, "wheel")
        paths.append([(r["state_start"], r["event"]) for r in rows])
        approx(rows[0]["fill"], OPENS["PE"][0] - slip)
    assert paths[0] == paths[1] == paths[2]
    r1 = wc.run_weeks(plans, CLOSES, make_loader(plans), 0.10, "wheel")[0]["premium_rs"]
    r3 = wc.run_weeks(plans, CLOSES, make_loader(plans), 0.30, "wheel")[0]["premium_rs"]
    approx(r1 - r3, 0.20 * Q)


# ------------------------------------------------------------------------------------------------ benchmark
def test_benchmark_arithmetic():
    plans = make_plans()
    b = wc.benchmark_weekly(plans, CLOSES)
    approx(b[0], (23650 - 24000) * Q - 0.00065 * 24000 * Q)
    approx(b[1], (23800 - 23650) * Q)
    approx(b[2], (24250 - 23800) * Q)
    approx(b[3], (24300 - 24250) * Q)
    approx(b[4], (23990 - 24300) * Q - 0.00065 * 23990 * Q)
    approx(sum(b), (23990 - 24000) * Q - 0.00065 * 24000 * Q - 0.00065 * 23990 * Q)  # buy at first entry spot, sell at the last close, both ends charged
    rows = wc.run_weeks(plans, CLOSES, make_loader(plans), 0.20, "wheel")
    for r, bb in zip(rows, b):
        approx(r["bench_rs"], bb)
        approx(r["d_rs"], r["net_rs"] - bb)


# ------------------------------------------------------------------------------------------------ skipped weeks
def test_skipped_weeks_are_counted_carried_and_kept_in_D():
    plans = make_plans()
    # week 0 put file missing: skipped; wheel stays CASH (no assignment even though the index fell below the strike); week 1 then sells a PUT, not a call
    rows = wc.run_weeks(plans, CLOSES, make_loader(plans, drop={(0, "PE")}), 0.20, "wheel")
    assert rows[0]["skipped"] == "missing_option_file" and rows[0]["event"] is None and rows[0]["state_end"] == "CASH"
    approx(rows[0]["net_rs"], 0.0)
    approx(rows[0]["d_rs"], 0.0 - rows[0]["bench_rs"])  # the week stays in D
    assert rows[1]["state_start"] == "CASH" and rows[1]["kind"] == "PE"
    s = wc.summarise(rows, 24000 * Q)
    assert s["n_weeks"] == 5 and s["n_skipped"] == 1 and s["n_traded"] == 4 and s["skipped"] == [("2026-01-08", "CASH", "missing_option_file")]
    # LONG week skipped (call file missing): exposure still marked, no call-away even though settle is above the call strike, stays LONG
    rows = wc.run_weeks(plans, CLOSES, make_loader(plans, drop={(2, "CE")}), 0.20, "wheel")
    assert rows[2]["skipped"] == "missing_option_file" and rows[2]["state_start"] == "LONG" and rows[2]["state_end"] == "LONG" and rows[2]["event"] is None
    approx(rows[2]["net_rs"], (24250 - 23800) * Q)
    assert rows[3]["state_start"] == "LONG" and rows[3]["kind"] == "CE"
    # no candle at the entry timestamp, no entry bar, nonpositive fill
    legs = make_loader(plans)
    odd = lambda ex, k, kind: (leg(datetime(2026, 1, 1, 9, 35), 50.0) if (ex, kind) == (EXP[0], "PE") else legs(ex, k, kind))  # noqa: E731
    assert wc.run_weeks(plans, CLOSES, odd, 0.20, "wheel")[0]["skipped"] == "no_candle_at_entry"
    p2 = make_plans()
    p2[0]["ts"] = None
    assert wc.run_weeks(p2, CLOSES, make_loader(plans), 0.20, "wheel")[0]["skipped"] == "no_entry_bar"
    cheap = {"PE": [0.15, 55.0, 50.0, 40.0, 45.0], "CE": OPENS["CE"]}
    assert wc.run_weeks(plans, CLOSES, make_loader(plans, cheap), 0.20, "wheel")[0]["skipped"] == "nonpositive_fill"


# ------------------------------------------------------------------------------------------------ controls
def test_control_put_only_never_holds_exposure():
    plans = make_plans()
    rows = wc.run_weeks(plans, CLOSES, make_loader(plans), 0.20, "put_only")
    assert all(r["state_start"] == "CASH" and r["state_end"] == "CASH" and r["kind"] == "PE" for r in rows)
    assert sum(r["expo_cost_rs"] for r in rows) == 0 and sum(r["exposure_mark_rs"] for r in rows) == 0
    assert [r["event"] for r in rows] == ["assigned", None, None, None, "assigned"]  # only a label: intrinsic paid, no exposure
    approx(rows[0]["net_rs"], 59.8 * Q - side_sell(59.8) - 50 * Q - 0.0015 * 50 * Q)


def test_control_call_only_is_always_long_and_keeps_exposure_when_called_away():
    plans = make_plans()
    rows = wc.run_weeks(plans, CLOSES, make_loader(plans), 0.20, "call_only")
    assert all(r["state_start"] == "LONG" and r["state_end"] == "LONG" and r["kind"] == "CE" for r in rows)
    approx(rows[0]["expo_cost_rs"], 0.00065 * 24000 * Q)  # entry
    approx(rows[4]["expo_cost_rs"], 0.00065 * 23990 * Q)  # exit
    assert rows[2]["event"] == "called_away" and rows[2]["expo_cost_rs"] == 0  # cash-settled: pays intrinsic, exposure kept, no re-buy cost
    approx(rows[2]["net_rs"], 24.8 * Q - side_sell(24.8) - 0.0015 * 150 * Q - 150 * Q + 450 * Q)


# ------------------------------------------------------------------------------------------------ no lookahead
def synthetic_bars(first=date(2026, 1, 1), n_days=75, base=24000.0):
    rows, px = [], base
    d = first
    for _ in range(n_days):
        if d.weekday() < 5:
            for i in range(75):
                t = datetime.combine(d, time(9, 15)) + timedelta(minutes=5 * i)
                o, c = px, px + (3 if i % 3 else -2)
                rows.append({"date": t, "open": o, "high": max(o, c) + 1, "low": min(o, c) - 1, "close": c, "volume": 0})
                px = c
        d += timedelta(days=1)
    return pd.DataFrame(rows)


def test_causal_entry_is_after_the_previous_expiry_and_as_written_is_not():
    bars = synthetic_bars()
    days = sorted(set(bars["date"].dt.date))
    # gaps of 7, 5 (Thu -> Tue), 8 days, and 6
    exps = [date(2026, 1, 8), date(2026, 1, 15), date(2026, 1, 20), date(2026, 1, 28), date(2026, 2, 3)]
    causal = wc.make_plans(bars, exps, 0, "causal")
    written = wc.make_plans(bars, exps, 0, "as_written")
    for k in range(1, len(exps)):
        assert causal[k]["entry_day"] > exps[k - 1], (k, causal[k]["entry_day"])
        assert causal[k]["entry_day"] < exps[k]
        assert causal[k]["ts"].time() == time(9, 30)
    assert written[1]["entry_day"] == exps[0]  # 7-day gap: as-written entry is the previous expiry's own day (lookahead for the state)
    assert causal[1]["entry_day"] == date(2026, 1, 9)
    assert causal[3]["entry_day"] == date(2026, 1, 21)  # 8-day gap: the selling-rule day (expiry-7d) is already after the previous expiry
    assert causal[3]["entry_day"] == written[3]["entry_day"]
    assert causal[0]["entry_day"] == written[0]["entry_day"] == date(2026, 1, 1)
    assert causal[1]["ts"] > datetime.combine(exps[0], time(15, 30))  # strictly after the previous settlement time


def test_decisions_use_only_candles_at_or_before_entry():
    bars = synthetic_bars()
    exps = [date(2026, 1, 8), date(2026, 1, 15), date(2026, 1, 22)]
    base = wc.make_plans(bars, exps)
    scrambled = bars.copy()
    for p in base:  # wreck every bar after each entry bar
        m = scrambled["date"] > p["ts"]
        scrambled.loc[m, ["open", "high", "low", "close"]] = 1.0
    again = wc.make_plans(scrambled, exps)
    # the first plan only sees bars up to ITS entry bar, so scrambling later bars (which are also later plans' entry bars) can only change later plans
    assert (again[0]["ts"], again[0]["spot"], again[0]["put_k"], again[0]["call_k"]) == (base[0]["ts"], base[0]["spot"], base[0]["put_k"], base[0]["call_k"])
    # wreck only bars after the LAST entry bar: nothing changes at all
    s2 = bars.copy()
    s2.loc[s2["date"] > base[-1]["ts"], ["open", "high", "low", "close"]] = 1.0
    assert wc.make_plans(s2, exps) == base
    # fills depend only on the entry candle; later option candles are irrelevant
    plans = make_plans()
    clean = make_loader(plans)
    noisy = lambda ex, k, kind: (None if clean(ex, k, kind) is None else leg(clean(ex, k, kind).index[0], clean(ex, k, kind).iloc[0]["open"], {clean(ex, k, kind).index[0] + timedelta(minutes=5): 999.0}))  # noqa: E731
    a = wc.run_weeks(plans, CLOSES, clean, 0.20, "wheel")
    b = wc.run_weeks(plans, CLOSES, noisy, 0.20, "wheel")
    assert [(r["fill"], r["net_rs"]) for r in a] == [(r["fill"], r["net_rs"]) for r in b]


def test_leg_choice_depends_only_on_earlier_settlements():
    plans = make_plans()
    base = wc.run_weeks(plans, CLOSES, make_loader(plans), 0.20, "wheel")
    for k in range(5):
        c = dict(CLOSES)
        c[EXP[k]] = CLOSES[EXP[k]] + 777.0  # change settlement k (and nothing else)
        alt = wc.run_weeks(plans, c, make_loader(plans), 0.20, "wheel")
        for j in range(k + 1):  # weeks 0..k choose their leg, strike, fill and start state before settlement k is known
            for f in ("state_start", "kind", "strike", "fill", "premium_rs", "fees_rs"):
                assert alt[j][f] == base[j][f] or (alt[j][f] != alt[j][f] and base[j][f] != base[j][f]), (k, j, f)
    # and the test is sensitive: flipping an EARLIER settlement does change the next leg
    c = dict(CLOSES)
    c[EXP[0]] = 24500.0  # no assignment in week 0
    alt = wc.run_weeks(plans, c, make_loader(plans), 0.20, "wheel")
    assert alt[1]["kind"] == "PE" and base[1]["kind"] == "CE"


# ------------------------------------------------------------------------------------------------ statistics
def test_halves_and_verdict_logic():
    rows = [{"expiry": date(2026, 1, 1) + timedelta(days=7 * i)} for i in range(5)]
    h = wc.halves_of(rows, [1, 2, 3, 4, 5])
    assert h["first_n"] == 3 and h["second_n"] == 2 and h["midpoint"] == "2026-01-15"  # expiry <= midpoint is the first half
    approx(h["first_mean"], 2.0)
    approx(h["second_mean"], 4.5)
    assert wc.verdict_of(10, 0.001, -100, -200, 5, 5)[0] == "SURVIVES"
    assert wc.verdict_of(10, 0.001, -300, -200, 5, 5)[0] == "INCONCLUSIVE"  # drawdown not smaller
    assert wc.verdict_of(10, 0.001, -100, -200, 5, -1)[0] == "INCONCLUSIVE"  # one half negative
    assert wc.verdict_of(10, 0.004, -100, -200, 5, 5)[0] == "REJECT"  # p above 0.05/14 = 0.003571
    assert wc.verdict_of(-1, 0.0001, -100, -200, 5, 5)[0] == "REJECT"  # mean D not positive
    approx(wc.ALPHA, 0.05 / 14)
    assert wc.TOTAL_TRIALS == 14


def test_series_stats_and_drawdown():
    s = wc.series_stats([100.0, -300.0, 50.0, 50.0, -20.0])
    approx(s["total"], -120.0)
    assert s["worst_week"] == -300.0 and s["best_week"] == 100.0
    # cumulative 100, -200, -150, -100, -120 ; peak 100 ; worst fall 100 -> -200 = -300
    approx(s["max_drawdown"], -300.0)
    approx(s["sharpe_like"], s["mean"] / np.std([100.0, -300.0, 50.0, 50.0, -20.0], ddof=1))


def test_bootstrap_p_direction():
    rng = np.random.default_rng(1)
    assert wc.fi.bootstrap_p(1000 + rng.normal(0, 10, 60)) < 0.01  # clearly positive mean
    assert wc.fi.bootstrap_p(rng.normal(0, 100, 60)) > 0.05  # noise


def test_summarise_matches_hand_totals():
    plans = make_plans()
    rows = wc.run_weeks(plans, CLOSES, make_loader(plans), 0.20, "wheel")
    s = wc.summarise(rows, 24000 * Q)
    b = wc.benchmark_weekly(plans, CLOSES)
    approx(s["bench"]["total"], sum(b))
    approx(s["D"]["total"], s["wheel"]["total"] - s["bench"]["total"])
    approx(s["total_return_wheel"], s["wheel"]["total"] / (24000 * Q))
    approx(s["premium_rs"] - s["intrinsic_paid_rs"] + s["exposure_marks_rs"] - s["option_fees_rs"] - s["settle_stt_rs"] - s["exposure_costs_rs"], s["wheel"]["total"])
    approx(s["idle_cash_info_rs"], sum(r["cash_info_rs"] for r in rows))
    assert rows[0]["cash_info_rs"] == 0.065 * (EXP[0] - ENTRY_DAYS[0]).days / 365 * 24000 * Q  # week 0 starts CASH: 7 days
    assert rows[1]["cash_info_rs"] == 0.0 and rows[3]["cash_info_rs"] > 0


# ------------------------------------------------------------------------------------------------ housekeeping
def test_no_code_opens_the_holdout_or_places_orders():
    for f in HERE.glob("*.py"):
        src = f.read_text()
        assert "nifty_holdout" not in src and "load_holdout" not in src, f
        assert not re.search(r"place_order|/order/place|orders/place|v2/order", src), f
        assert not re.search(r"print\([^)]*TOKEN|open\([^)]*TOKEN", src), f


def test_ledger_record_appends_one_trial_and_refuses_twice():
    sys.path.insert(0, str(HERE.parent / "ideas" / "loop"))
    import loop_config as cfg
    import trial_ledger as tl
    import wheel_run as wr
    with tempfile.TemporaryDirectory() as td:
        paths = cfg.Paths(ledger=Path(td) / "ledger_loop.jsonl")
        for i in range(13):
            tl.append({"event": "trial", "idea_id": f"X-{i}"}, paths)
        assert tl.total_trials(paths) == 13
        fake = {"primary": {"n_traded": 79, "n_weeks": 81, "D": {"mean": -12.5}, "boot_p": 0.7, "verdict": "REJECT", "checks": {"a": False}}}
        wr.record(fake, paths=paths)
        assert tl.total_trials(paths) == 14 and tl.verify(paths) == 15  # 13 trials + batch_start + the new trial
        ev = tl.trial_for("B4-01", paths)
        assert ev["verdict"] == "REJECT" and abs(ev["alpha"] - 0.05 / 14) < 1e-12 and ev["batch"] == 4
        try:
            wr.record(fake, paths=paths)
            raise AssertionError("second record should refuse")
        except SystemExit:
            pass
        assert tl.total_trials(paths) == 14


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"{len(fns)} tests passed")
