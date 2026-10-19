"""Task 11 (gold/silver pair, B6-01) self-checks with hand-computed numbers: ratio Z-score and rolling window (window ENDS at t,
uses only data through t), trade at the NEXT open, exit rules (|Z|<=0.5, 20-day time stop, |Z|>=4 stop), equal-notional two-leg P&L,
costs and financing drag, skipped-day accounting, one-position-at-a-time, no lookahead, statistics, null-helper equivalence.
No market data files needed.   Run:  python research/goldsilver/tests/test_goldsilver.py   (also collected by pytest)."""

import math
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import gs_core as gc  # noqa: E402


def approx(a, b, tol=1e-9):
    assert abs(a - b) <= tol, (a, b)


def frame(r, g_open, s_open, start="2024-01-01"):
    """Calendar frame. r[t] = ln(gold close / silver close); silver close = 1, so gold close = exp(r). Weekdays from `start` (a Monday)."""
    n = len(r)
    dates = pd.bdate_range(start, periods=n)
    return pd.DataFrame({"date": dates, "g_open": np.asarray(g_open, float), "g_close": np.exp(np.asarray(r, float)),
                         "s_open": np.asarray(s_open, float), "s_close": np.ones(n)})


def flat_open(n, v=100.0):
    return [v] * n


# ------------------------------------------------------------------------------------------ Z-score and window
def test_zscore_hand_computed_and_window_ends_at_t():
    r = [0.0, 0.0, 3.0, 1.0]
    z = gc.zscore(np.exp(r), np.ones(4), lookback=3)
    assert np.isnan(z[0]) and np.isnan(z[1])  # fewer than 3 values: undefined
    approx(z[2], (3 - 1) / math.sqrt(3))  # window [0,0,3]: mean 1, sample std sqrt(6/2)=sqrt3
    # window [0,3,1] (rows 1..3, includes t=3): mean 4/3, sum sq dev = 42/9, std = sqrt(21/9)
    approx(z[3], (1 - 4 / 3) / math.sqrt(21 / 9))
    # a window of identical values has zero std: no signal
    assert np.isnan(gc.zscore(np.exp([1, 1, 1, 1.0]), np.ones(4), 3)[2])


def test_zscore_uses_ratio_not_levels():
    g, s = np.array([10.0, 20, 30, 40]), np.array([5.0, 10, 15, 20])  # ratio constant 2 -> std 0 -> NaN
    assert np.isnan(gc.zscore(g, s, 3)).all()
    g2 = np.array([10.0, 20, 30, 80])  # ratio 2,2,2,4 -> window rows 1..3 = ln(2),ln(2),ln(4)
    z = gc.zscore(g2, s, 3)
    a, b = math.log(2), math.log(4)
    m = (2 * a + b) / 3
    sd = math.sqrt(((a - m) ** 2 * 2 + (b - m) ** 2) / 2)
    approx(z[3], (b - m) / sd)


def test_60_day_window_known_value():
    # 59 zeros then a spike a: Z = 59/sqrt(60) whatever a is (derived by hand in the pre-registration notes)
    r = [0.0] * 59 + [0.7]
    z = gc.zscore(np.exp(r), np.ones(60), 60)
    approx(z[59], 59 / math.sqrt(60))
    assert np.isnan(z[:59]).all()


def test_no_lookahead_in_z():
    rng = np.random.default_rng(1)
    r = rng.normal(0, 0.01, 120)
    z1 = gc.zscore(np.exp(r), np.ones(120), 60)
    r2 = r.copy()
    r2[100:] += 5.0  # change the future
    z2 = gc.zscore(np.exp(r2), np.ones(120), 60)
    assert np.array_equal(z1[:100], z2[:100], equal_nan=True)
    assert not np.array_equal(z1[100:], z2[100:], equal_nan=True)


# ------------------------------------------------------------------------------------------ entry, exits, P&L
def test_gold_expensive_sells_gold_buys_silver_next_open_hand_pnl():
    # lookback 3: Z2 = 1.1547 >= entry 1.1 -> signal at the close of row 2, entry at the OPEN of row 3.
    # Z3 = -0.2182 -> |Z| <= 0.5 at the close of the entry day -> exit at the open of row 4.
    r = [0, 0, 3, 1, 0, 0, 0]
    go = [90, 91, 92, 100, 102, 103, 104]  # signal-day close/other opens must not matter; entry 100, exit 102
    so = [40, 41, 42, 50, 49, 48, 47]  # entry 50, exit 49
    out = gc.simulate(frame(r, go, so), lookback=3, entry=1.1)
    t = out["trades"]
    assert len(t) >= 1
    x = t[0]
    assert (x["signal_row"], x["entry_row"], x["exit_row"], x["direction"], x["reason"], x["hold"]) == (2, 3, 4, -1, "revert", 1)
    # sold gold (+2% against us), bought silver (-2% against us): -4% of one-leg notional
    approx(x["gross"], -((102 / 100 - 1) - (49 / 50 - 1)))
    approx(x["gross"], -0.04)
    assert x["cal_days"] == 1  # Thu 2024-01-04 -> Fri 2024-01-05
    approx(gc.net_returns([x])[0], -0.04 - 0.002 - 0.0002 * 1)


def test_gold_cheap_buys_gold_sells_silver():
    r = [0, 0, -3, -1, 0, 0, 0]
    go = [90, 91, 92, 100, 103, 103, 104]
    so = [40, 41, 42, 50, 49, 48, 47]
    x = gc.simulate(frame(r, go, so), lookback=3, entry=1.1)["trades"][0]
    assert x["direction"] == +1 and x["reason"] == "revert"
    approx(x["gross"], (103 / 100 - 1) - (49 / 50 - 1))  # long gold +3%, short silver -2% falls = +2%: +5%
    approx(x["gross"], 0.05)


def test_entry_uses_next_open_not_signal_close_or_signal_open():
    r = [0, 0, 3, 1, 0, 0, 0]
    base = gc.simulate(frame(r, [90, 91, 92, 100, 102, 103, 104], [40, 41, 42, 50, 49, 48, 47]), 3, 1.1)["trades"][0]
    changed = gc.simulate(frame(r, [999, 999, 999, 100, 102, 103, 104], [999, 999, 999, 50, 49, 48, 47]), 3, 1.1)["trades"][0]
    approx(base["gross"], changed["gross"])  # opens on and before the signal day are irrelevant


def test_stop_exit_scaled_down_and_one_position_at_a_time():
    # r = [0,0,3,6,...]: Z2 = 1.1547 (signal), Z3 = 1.0. With stop 0.9: the stop fires at the close of the entry day (row 3).
    # Z3 also exceeds entry 0.95, but the position is still open at that close, so NO new trade can start there.
    r = [0, 0, 3, 6, 6.2, 6.1, 6.0, 6.3]
    out = gc.simulate(frame(r, flat_open(8), flat_open(8)), lookback=3, entry=0.95, stop=0.9)
    x = out["trades"][0]
    assert (x["signal_row"], x["entry_row"], x["exit_row"], x["reason"]) == (2, 3, 4, "stop")
    assert all(t["entry_row"] != 4 for t in out["trades"])  # no re-entry on the exit trigger close
    assert len(out["trades"]) == 1 or out["trades"][1]["signal_row"] >= 4  # next signal not before the exit-open day's close


def test_time_stop_after_20_trading_days_default():
    rng = np.random.default_rng(7)
    r = [0.0, 0.0, 3.0] + list(rng.normal(1.0, 0.3, 40))
    out = gc.simulate(frame(r, flat_open(43), flat_open(43)), lookback=3, entry=1.1, exit_=0.0, stop=50.0)  # exit/stop never fire
    x = out["trades"][0]
    assert (x["signal_row"], x["entry_row"], x["exit_row"], x["hold"], x["reason"]) == (2, 3, 23, 20, "time")


def test_time_stop_short_version_and_unfinished_trade():
    r = [0, 0, 3, 1.4, 1.2, 1.0, 1.1, 1.3]
    out = gc.simulate(frame(r, flat_open(8), flat_open(8)), lookback=3, entry=1.1, exit_=0.0, stop=50.0, max_hold=3)
    x = out["trades"][0]
    assert (x["entry_row"], x["exit_row"], x["hold"], x["reason"]) == (3, 6, 3, "time")
    # data ends before the exit open exists: unfinished, dropped from the trades
    out = gc.simulate(frame(r[:5], flat_open(5), flat_open(5)), lookback=3, entry=1.1, exit_=0.0, stop=50.0, max_hold=3)
    assert out["trades"] == [] and out["unfinished"] == 1


def test_default_constants_60_day_spike_stop_and_revert():
    a = 0.7
    # spike on row 59 (Z = 7.6 >= 2: sell gold, buy silver); it stays -> Z60 = (a - 2a/60)/sd = 5.34 >= 4 -> stop, exit open row 61
    r = [0.0] * 59 + [a, a, a, a]
    out = gc.simulate(frame(r, flat_open(63), flat_open(63)))
    x = out["trades"][0]
    vals = np.array([0.0] * 58 + [a, a])
    approx(float(out["z"][60]), (a - vals.mean()) / vals.std(ddof=1))
    assert float(out["z"][60]) >= 4.0
    assert (x["signal_row"], x["entry_row"], x["exit_row"], x["direction"], x["reason"]) == (59, 60, 61, -1, "stop")
    # spike reverses at once: Z60 = -sqrt(60)/60 = -0.129 -> |Z| <= 0.5 -> revert at the entry-day close
    r = [0.0] * 59 + [a, 0.0, 0.0, 0.0]
    x = gc.simulate(frame(r, flat_open(63), flat_open(63)))["trades"][0]
    assert (x["entry_row"], x["exit_row"], x["reason"]) == (60, 61, "revert")


def test_thresholds_are_inclusive_and_no_trade_below():
    # r = [0,0,3,...] gives Z2 = 2/sqrt(3) exactly. entry = that value -> trades; entry slightly above -> none.
    z2 = 2 / math.sqrt(3)
    r = [0, 0, 3, 1, 0, 0]
    df = frame(r, flat_open(6), flat_open(6))
    assert len(gc.simulate(df, 3, z2)["trades"]) >= 1
    assert gc.simulate(df, 3, z2 + 1e-6)["trades"] == []


def test_signal_on_last_row_is_skipped_signal():
    out = gc.simulate(frame([0, 0, 3], flat_open(3), flat_open(3)), 3, 1.1)
    assert out["trades"] == [] and out["skipped_signals"] == 1 and out["unfinished"] == 0


# ------------------------------------------------------------------------------------------ costs and financing
def test_costs_and_financing_drag():
    approx(float(gc.trade_cost(30, 20)), 0.002 + 0.0002 * 30)  # calendar days
    approx(float(gc.trade_cost(30, 20, "trading")), 0.002 + 0.0002 * 20)  # information-only reading
    approx(float(gc.trade_cost(0, 0, "calendar", 0.0, 0.0)), 0.0)
    tr = [{"gross": 0.05, "cal_days": 30, "hold": 20}]
    approx(gc.net_returns(tr)[0], 0.05 - 0.002 - 0.006)  # = 0.042
    approx(gc.net_returns(tr, zero_cost=True)[0], 0.05)
    # weekend counts: entry Friday open, exit Monday open = 3 calendar days = 0.06%
    r = [0, 0, 3, 1, 0, 0, 0]
    out = gc.simulate(frame(r, flat_open(7), flat_open(7), start="2024-01-03"), 3, 1.1)["trades"][0]  # entry Mon... check below
    assert out["cal_days"] == int((pd.Timestamp(out["exit_date"]) - pd.Timestamp(out["entry_date"])).days)
    df = frame([0, 0, 3, 1, 0, 0, 0], flat_open(7), flat_open(7), start="2024-01-01")
    df["date"] = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-05", "2024-01-08", "2024-01-09", "2024-01-10"])
    x = gc.simulate(df, 3, 1.1)["trades"][0]
    assert (x["entry_date"], x["exit_date"], x["cal_days"]) == ("2024-01-05", "2024-01-08", 3)


# ------------------------------------------------------------------------------------------ skipped-day accounting and cutoff
def test_load_skipped_days_and_cutoff():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        base = ["date,open,high,low,close,volume"]
        g = base + ["2022-01-03,10,11,9,10,5", "2022-02-07,10,11,9,10,5", "2022-02-08,10,11,9,10,5", "2022-02-09,10,11,9,10,5",
                    "2022-02-10,10,11,9,10,0", "2022-02-11,10,11,9,10,5", "2026-04-16,10,11,9,10,5", "2026-04-17,10,11,9,10,5", "2026-05-04,10,11,9,10,5"]
        s = base + ["2022-02-07,20,21,19,20,5", "2022-02-08,20,21,19,20,5", "2022-02-10,20,21,19,20,5", "2022-02-11,0,21,19,20,5",
                    "2022-02-12,20,21,19,20,5", "2026-04-16,20,21,19,20,5", "2026-04-17,20,21,19,20,5"]
        (d / "g.csv").write_text("\n".join(g) + "\n")
        (d / "s.csv").write_text("\n".join(s) + "\n")
        df, sk = gc.load(d / "g.csv", d / "s.csv")
        # gold only: 2022-02-09; silver only: 2022-02-12 (Sat row); bad price: 2022-02-11 (silver open 0)
        assert sk["only_gold"] == ["2022-02-09"] and sk["only_silver"] == ["2022-02-12"] and sk["bad_price_rows"] == ["2022-02-11"]
        assert sk["n_skipped_days"] == 3 and sk["zero_volume_days"] == 1 and sk["gold_rows_before_silver_listed"] == 1
        assert sk["silver_first_date"] == "2022-02-07"
        assert [str(x.date()) for x in df["date"]] == ["2022-02-07", "2022-02-08", "2022-02-10", "2026-04-16"]
        assert df["date"].max() <= gc.CUTOFF and sk["last_date"] == "2026-04-16"  # nothing after the cutoff survives


# ------------------------------------------------------------------------------------------ statistics
def test_max_drawdown_hand_computed():
    approx(gc.max_drawdown(np.array([0.02, -0.03, 0.01, -0.04, 0.05])), -0.06)  # peak +0.02 -> trough -0.04
    approx(gc.max_drawdown(np.array([-0.01, -0.02])), -0.03)  # starts from 0
    approx(gc.max_drawdown(np.array([0.01, 0.02])), 0.0)


def test_halves_split_at_calendar_midpoint_by_entry_date():
    tr = [{"entry_date": d} for d in ("2022-01-02", "2022-06-30", "2022-07-02", "2022-12-31")]
    net = np.array([1.0, 2.0, -3.0, -5.0])
    h = gc.halves(tr, net, "2022-01-01", "2023-01-01")  # midpoint 2022-07-02 (182 days after Jan 1), entry ON the midpoint is first half
    assert h["midpoint"] == "2022-07-02"
    assert (h["first_n"], h["second_n"]) == (3, 1)
    approx(h["first_mean"], 0.0)
    approx(h["second_mean"], -5.0)


def test_bootstrap_p_extremes():
    approx(gc.fi.bootstrap_p(np.full(30, 0.01), gc.BLOCK, 1000, gc.SEED), 1 / 1001)
    approx(gc.fi.bootstrap_p(np.full(30, -0.01), gc.BLOCK, 1000, gc.SEED), 1.0)


def test_verdict_rules():
    base = dict(n_trades=20, mean_net=0.01, boot_p=0.001, null_p=0.001, first_n=10, second_n=10, first_mean=0.01, second_mean=0.01)
    assert gc.verdict(base)[1] == "PASS"
    assert gc.verdict({**base, "n_trades": 14})[1] == "INCONCLUSIVE"  # too few, whatever the mean
    assert gc.verdict({**base, "n_trades": 3, "boot_p": 0.0001})[1] == "INCONCLUSIVE"
    assert gc.verdict({**base, "boot_p": 0.004})[1] == "REJECT"  # alpha is 0.003125
    assert gc.verdict({**base, "null_p": 0.0032})[1] == "REJECT"
    assert gc.verdict({**base, "second_mean": -0.001})[1] == "REJECT"
    assert gc.verdict({**base, "mean_net": -0.001})[1] == "REJECT"
    approx(gc.ALPHA, 0.05 / 16)


def test_null_matches_repo_null_p_when_cost_is_scalar():
    rng = np.random.default_rng(3)
    n = 90
    px = lambda: 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))  # noqa: E731
    df = pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=n), "g_open": px(), "s_open": px()})
    hold = [3, 3, 3, 7, 7]
    dirs = [+1, -1, -1, +1, +1]
    trades = [{"hold": h, "direction": d, "gross": 0.01 * d, "cal_days": 0} for h, d in zip(hold, dirs)]  # our gross already has the sign
    first = 10
    cand = {h: gc.null_candidates(df, h, first, financing="calendar", cost_rt=0.0, fin=0.0)[0] for h in set(hold)}
    # the repo helper's `gross` is the LONG gross per trade and net = direction x gross - cost; 0.01 for every trade gives the same observed mean
    ft = gc.fi.Trades(0, "x", np.array(["2024-01-01"] * 5, dtype="datetime64[D]"), np.array(dirs), np.full(5, 0.01),
                      np.array(hold), cand, (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-06-01")))
    p1, m1, q1 = gc.fi.null_p(ft, cost=0.002, n_draw=2000)
    p2, m2, q2 = gc.gs_null_p(df, trades, first, n_draw=2000, financing="calendar", cost_rt=0.002, fin=0.0)
    approx(p1, p2, 1e-12)
    approx(m1, m2, 1e-9)
    approx(q1, q2, 1e-9)


def test_null_p_per_candidate_financing_changes_cost():
    rng = np.random.default_rng(4)
    n = 60
    px = lambda: 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))  # noqa: E731
    df = pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=n), "g_open": px(), "s_open": px()})
    g0, c0 = gc.null_candidates(df, 3, 10, "calendar", 0.0, 0.0)
    g1, c1 = gc.null_candidates(df, 3, 10, "calendar", 0.002, 0.0002)
    assert np.allclose(g0, g1) and np.allclose(c0, 0.0)
    d = df["date"].to_numpy("datetime64[D]")
    cal = (d[13:] - d[10:-3]).astype(int)
    assert np.allclose(c1, 0.002 + 0.0002 * cal)
    assert set(cal) == {3, 5}  # 3 trading days = 3 calendar days inside a week, 5 across a weekend
    _, ct = gc.null_candidates(df, 3, 10, "trading", 0.002, 0.0002)
    assert np.allclose(ct, 0.002 + 0.0002 * 3)


def test_evaluate_base_cell_equals_default_and_is_deterministic():
    rng = np.random.default_rng(11)
    n = 400
    r = np.cumsum(rng.normal(0, 0.01, n)) * 0.3 + rng.normal(0, 0.02, n)
    df = frame(r, 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n))), 50 * np.exp(np.cumsum(rng.normal(0, 0.01, n))))
    a = gc.evaluate(df, with_null=False)
    b = gc.evaluate(df, 60, 2.0, with_null=False)
    assert pd.Series(a, dtype=object).astype(str).equals(pd.Series(b, dtype=object).astype(str))  # NaN-safe equality
    assert a["n_trades"] >= 1


# ------------------------------------------------------------------------------------------ hygiene
def test_no_holdout_no_orders_no_secrets_in_source():
    pat_hold = "nifty" + "_holdout"
    for p in HERE.glob("*.py"):
        src = p.read_text()
        assert pat_hold not in src, p.name
        assert not re.search(r"place_?order|\.order\(|kite\.|UPSTOX_ANALYTICS_TOKEN\s*=", src, re.I), p.name
        assert not re.search(r"print\(.*token", src, re.I), p.name


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"{len(fns)} tests passed")
