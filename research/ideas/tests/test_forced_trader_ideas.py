"""Task 5 self-checks: every rule on tiny hand-made data with known answers, cost handling, no-lookahead, calendar rules
(holiday gaps, expiry weekday switch, real expiry list), bootstrap / null / verdict helpers.
Run:  python research/ideas/tests/test_forced_trader_ideas.py   (also collected by pytest)."""

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import forced_trader_ideas as fi  # noqa: E402


def approx(a, b, tol=1e-9):
    assert abs(a - b) <= tol, (a, b)


def daily(rows):
    """rows: list of (date string, open, close)."""
    return pd.DataFrame({"date": pd.to_datetime([r[0] for r in rows]), "open": [r[1] for r in rows], "close": [r[2] for r in rows]})


def synth_daily(start="2024-01-01", n=40, price=100.0):
    dts = pd.bdate_range(start, periods=n)
    return daily([(str(x.date()), price, price) for x in dts])


# ------------------------------------------------------------------ costs
def test_cost_applies_to_long_and_short():
    t = fi._trades(0, "x", ["2024-01-02", "2024-01-03"], [1, -1], [0.01, 0.01], [0, 0], {0: np.array([0.01, 0.01])}, (date(2024, 1, 1), date(2024, 1, 5)))
    approx(t.net()[0], 0.01 - 0.001)
    approx(t.net()[1], -0.01 - 0.001)
    approx(t.net(0.0)[1], -0.01)


# ------------------------------------------------------------------ idea 1
def test_idea1_second_last_to_third_day():
    d = daily([("2024-01-29", 100, 100), ("2024-01-30", 100, 110), ("2024-01-31", 100, 111),
               ("2024-02-01", 100, 112), ("2024-02-02", 100, 113), ("2024-02-05", 100, 121.0),
               ("2024-02-06", 100, 122), ("2024-02-27", 100, 123), ("2024-02-28", 100, 124), ("2024-02-29", 100, 125),
               ("2024-03-01", 100, 126), ("2024-03-04", 100, 127), ("2024-03-05", 100, 128)])
    t = fi.idea1_sip(d)
    # Jan: 2nd-last trading day = 01-30 (close 110); 3rd trading day of Feb = 02-05 (close 121)
    assert len(t.gross) == 2  # Jan->Feb and Feb->Mar; March (last month in file) is skipped
    approx(t.gross[0], 121 / 110 - 1)
    assert str(t.entry_date[0]) == "2024-01-30"
    # Feb: 2nd-last = 02-28 (124); 3rd day of March = 03-05 (128)
    approx(t.gross[1], 128 / 124 - 1)
    assert (t.direction == 1).all()


def test_idea1_partial_last_month_skipped():
    d = daily([("2024-01-30", 1, 100), ("2024-01-31", 1, 100), ("2024-02-01", 1, 100), ("2024-02-02", 1, 100)])
    assert len(fi.idea1_sip(d).gross) == 0  # Feb has only 2 rows and is the last month: nothing to enter or exit on


# ------------------------------------------------------------------ idea 2
def test_idea2_overnight_close_to_next_open():
    d = daily([("2024-01-02", 99, 100), ("2024-01-03", 101, 102), ("2024-01-04", 100, 103)])
    t = fi.idea2_overnight(d)
    approx(t.gross[0], 101 / 100 - 1)
    approx(t.gross[1], 100 / 102 - 1)
    assert len(t.gross) == 2
    i = fi.idea2_intraday_info(d)
    approx(i.gross[0], 100 / 99 - 1)


# ------------------------------------------------------------------ idea 3
def test_idea3_gap_threshold_strict_and_direction():
    d = daily([("2024-01-02", 100, 100), ("2024-01-03", 100.69, 100.0),   # gap +0.69%: no trade
               ("2024-01-04", 100.71, 100.0),                              # gap +0.71% vs prev close 100.0 -> fade = short
               ("2024-01-05", 99.2, 99.5),                                  # gap -0.8% -> long
               ("2024-01-08", 99.5 * 1.007, 100)])                          # exactly +0.7%: NOT traded (strictly more than)
    t = fi.idea3_gap_fade(d)
    assert [str(x) for x in t.entry_date] == ["2024-01-04", "2024-01-05"]
    assert list(t.direction) == [-1, 1]
    approx(t.gross[0], 100.0 / 100.71 - 1)  # long gross; net = -gross for the short
    approx(t.net(0.0)[0], -(100.0 / 100.71 - 1))


def test_idea3_uses_only_open_and_prior_close_for_signal():
    d = daily([("2024-01-02", 100, 100), ("2024-01-03", 101, 90)])
    d2 = d.copy()
    d2.loc[1, "close"] = 120  # change the trade day's close: the signal (direction) must not change
    assert list(fi.idea3_gap_fade(d).direction) == list(fi.idea3_gap_fade(d2).direction) == [-1]


# ------------------------------------------------------------------ idea 4
def test_idea4_down_2pct_then_next_day_open_to_close():
    d = daily([("2024-01-02", 100, 100), ("2024-01-03", 100, 98.0),    # -2.0% exactly: counts ("2% or more")
               ("2024-01-04", 97, 99.0),                                # traded: open 97 -> close 99
               ("2024-01-05", 99, 97.5),                                # -1.5%: no signal
               ("2024-01-08", 97, 95.0),                                # -2.56%: signal, but it is on... next row
               ("2024-01-09", 94, 96.0)])
    t = fi.idea4_forced_sellers(d)
    assert [str(x) for x in t.entry_date] == ["2024-01-04", "2024-01-09"]
    approx(t.gross[0], 99 / 97 - 1)
    approx(t.gross[1], 96 / 94 - 1)


def test_idea4_last_row_signal_has_no_trade():
    d = daily([("2024-01-02", 100, 100), ("2024-01-03", 100, 90)])
    assert len(fi.idea4_forced_sellers(d).gross) == 0


# ------------------------------------------------------------------ idea 5
def test_idea5_vix_spike_long_close_to_close_3_rows():
    d = daily([("2024-01-01", 1, 100), ("2024-01-02", 1, 101), ("2024-01-03", 1, 102),
               ("2024-01-04", 1, 103), ("2024-01-05", 1, 104), ("2024-01-08", 1, 105)])
    v = pd.DataFrame({"date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]),
                      "close": [10, 11.5, 11.5, 11.4, 12.0, 14.0]})
    # 01-02: +15.0% (counts); 01-05: +5.3% no; 01-08: +16.7% but exit is beyond the data -> dropped and counted
    t = fi.idea5_vix_panic(d, v)
    assert [str(x) for x in t.entry_date] == ["2024-01-02"]
    approx(t.gross[0], 104 / 101 - 1)  # close(01-02) -> close 3 rows later (01-05)
    assert t.skipped == 1


def test_idea5_vix_below_threshold_ignored():
    d = synth_daily(n=10)
    v = pd.DataFrame({"date": d["date"], "close": np.linspace(10, 11, 10)})
    assert len(fi.idea5_vix_panic(d, v).gross) == 0


# ------------------------------------------------------------------ ideas 6 and 7 (5-minute)
def mk5(day, prices):
    """prices: {HHMM: (open, close)}; returns rows for one day."""
    return [(pd.Timestamp(f"{day} {t[:2]}:{t[2:]}"), o, c) for t, (o, c) in prices.items()]


def frame5(rows):
    return pd.DataFrame(rows, columns=["date", "open", "close"]).assign(high=0.0, low=0.0, volume=0)


def test_idea6_signal_uses_opens_and_trades_open_1515_to_close_1525():
    rows = mk5("2024-01-02", {"1415": (100, 100.2), "1515": (101, 101.4), "1520": (101.4, 101.5), "1525": (101.5, 102.0)})
    t = fi.idea6_closing(frame5(rows))
    assert list(t.direction) == [1]  # 101 > 100
    approx(t.gross[0], 102.0 / 101 - 1)
    # falling afternoon -> short
    rows2 = mk5("2024-01-03", {"1415": (100, 99), "1515": (99, 99), "1520": (99, 98.9), "1525": (98.9, 98.5)})
    t2 = fi.idea6_closing(frame5(rows + rows2))
    assert list(t2.direction) == [1, -1]
    approx(t2.net(0.0)[1], -(98.5 / 99 - 1))


def test_idea6_no_lookahead_signal_ignores_the_trade_bar_after_its_open():
    rows = mk5("2024-01-02", {"1415": (100, 100.2), "1515": (101, 101.4), "1525": (101.5, 102.0)})
    rows_b = mk5("2024-01-02", {"1415": (100, 100.2), "1515": (101, 50.0), "1525": (101.5, 102.0)})  # 15:15 CLOSE differs (future of the signal)
    assert list(fi.idea6_closing(frame5(rows)).direction) == list(fi.idea6_closing(frame5(rows_b)).direction)


def test_idea6_missing_bar_skips_day_and_counts():
    rows = mk5("2024-01-02", {"1415": (100, 100), "1515": (101, 101), "1525": (101, 102)})
    rows += mk5("2024-01-03", {"1415": (100, 100), "1515": (101, 101)})  # no 15:25 bar (e.g. a special session)
    t = fi.idea6_closing(frame5(rows))
    assert len(t.gross) == 1 and t.skipped == 1


def test_idea7_first_30min_sign_trade_0945_open_to_1515_open():
    rows = mk5("2024-01-02", {"0915": (100, 100.1), "0940": (100.5, 101.0), "0945": (101.0, 101.2), "1515": (102.0, 102.5)})
    t = fi.idea7_morning(frame5(rows))
    assert list(t.direction) == [1]  # 101.0 / 100 - 1 > 0
    approx(t.gross[0], 102.0 / 101.0 - 1)
    rows2 = mk5("2024-01-03", {"0915": (100, 99), "0940": (99.5, 99.0), "0945": (99.0, 98.8), "1515": (98.0, 98.2)})
    t2 = fi.idea7_morning(frame5(rows2))
    assert list(t2.direction) == [-1]
    approx(t2.net(0.0)[0], -(98.0 / 99.0 - 1))


def test_idea7_signal_unchanged_by_anything_from_0945_on():
    base = {"0915": (100, 100.1), "0940": (100.5, 101.0), "0945": (101.0, 101.2), "1515": (102.0, 102.5)}
    alt = dict(base, **{"0945": (60.0, 40.0), "1515": (200.0, 1.0)})  # everything at/after 09:45 changed
    assert list(fi.idea7_morning(frame5(mk5("2024-01-02", base))).direction) == list(fi.idea7_morning(frame5(mk5("2024-01-02", alt))).direction)


# ------------------------------------------------------------------ idea 8
def test_idea8_holiday_gap_rules():
    d = daily([("2024-01-02", 100, 100),   # Tue
               ("2024-01-03", 101, 101),   # Wed
               ("2024-01-05", 102, 102),   # Fri  (Thu 01-04 closed -> Wed is pre-holiday)
               ("2024-01-08", 103, 103),   # Mon  (Fri->Mon is a normal weekend: Fri not pre-holiday; Mon IS, see below)
               ("2024-01-11", 104, 104),   # Thu  (Tue 09, Wed 10 closed -> Mon is pre-holiday, ONE trade)
               ("2024-01-12", 105, 105),   # Fri  (Thu->Fri normal)
               ("2024-01-17", 106, 106),   # Wed  (Mon 15 closed -> Fri 12 pre-holiday: Fri->Wed gap 5 days)
               ("2024-01-18", 107, 107)])
    t = fi.idea8_preholiday(d)
    assert [str(x) for x in t.entry_date] == ["2024-01-03", "2024-01-08", "2024-01-12"]
    approx(t.gross[0], 102 / 101 - 1)  # close of Wed -> open of Fri
    approx(t.gross[1], 104 / 103 - 1)
    approx(t.gross[2], 106 / 105 - 1)


def test_idea8_friday_holiday_thursday_is_the_trade():
    d = daily([("2024-03-27", 1, 100), ("2024-03-28", 1, 101), ("2024-04-01", 103, 102)])  # Fri 03-29 closed (Good Friday)
    t = fi.idea8_preholiday(d)
    assert [str(x) for x in t.entry_date] == ["2024-03-28"]


def test_idea8_saturday_special_session_is_not_a_holiday_gap():
    d = daily([("2024-03-01", 1, 100), ("2024-03-02", 1, 101), ("2024-03-04", 1, 102)])  # Fri, Sat special session, Mon
    assert len(fi.idea8_preholiday(d).gross) == 0


# ------------------------------------------------------------------ idea 9
def test_idea9_friday_close_to_monday_close_and_skip_when_monday_closed():
    d = daily([("2024-01-05", 1, 100), ("2024-01-08", 1, 103),            # Fri -> Mon traded
               ("2024-01-12", 1, 105), ("2024-01-16", 1, 104),             # Fri -> Tue (Mon closed): skipped
               ("2024-01-19", 1, 106), ("2024-01-22", 1, 107)])            # Fri -> Mon traded
    t = fi.idea9_weekend(d)
    assert [str(x) for x in t.entry_date] == ["2024-01-05", "2024-01-19"]
    approx(t.gross[0], 3 / 100)
    approx(t.gross[1], 107 / 106 - 1)
    assert t.skipped == 1


# ------------------------------------------------------------------ idea 10
def test_expiry_weekday_switch_and_holiday_shift():
    # Thursday up to 2025-08-28, Tuesday from 2025-09-02; a closed expiry weekday moves to the previous trading row
    days = pd.bdate_range("2025-08-18", "2025-09-12")
    days = days.drop([pd.Timestamp("2025-09-09")])  # Tuesday 09-09 closed -> expiry Monday 09-08
    d = daily([(str(x.date()), 100, 100) for x in days])
    got = [str(x.date()) for x in d["date"].iloc[fi.expiry_rows(d)]]
    assert got == ["2025-08-21", "2025-08-28", "2025-09-02", "2025-09-08"], got


def test_idea10_direction_from_previous_day_and_thursday_trade():
    # Thursday 2024-01-04; prev day (Wed 01-03) return = +2% -> long on Thursday; Thursday 01-11: Wed fell -> short
    d = daily([("2024-01-01", 100, 100), ("2024-01-02", 100, 100), ("2024-01-03", 100, 102.0), ("2024-01-04", 102, 103.0),
               ("2024-01-05", 103, 104), ("2024-01-08", 104, 104), ("2024-01-09", 104, 104), ("2024-01-10", 104, 100.0),
               ("2024-01-11", 100, 98.0)])
    t = fi.idea10_expiry(d)
    assert [str(x) for x in t.entry_date] == ["2024-01-04", "2024-01-11"]
    assert list(t.direction) == [1, -1]
    approx(t.gross[0], 103 / 102 - 1)
    approx(t.net(0.0)[1], -(98 / 100 - 1))


def test_expiry_skips_muhurat_session_day():
    # Tue 2025-10-21 is a Muhurat-only day: the Tuesday expiry moves to Monday 10-20
    days = pd.to_datetime(["2025-10-14", "2025-10-15", "2025-10-16", "2025-10-17", "2025-10-20", "2025-10-21", "2025-10-23"])
    d = daily([(str(x.date()), 100, 100) for x in days])
    got = [str(x.date()) for x in d["date"].iloc[fi.expiry_rows(d)]]
    assert got == ["2025-10-14", "2025-10-20"], got


def test_idea10_signal_does_not_use_the_expiry_days_own_prices():
    d = daily([("2024-01-02", 100, 100), ("2024-01-03", 100, 102.0), ("2024-01-04", 102, 103.0)])
    d2 = d.copy()
    d2.loc[2, "close"] = 10.0
    assert list(fi.idea10_expiry(d).direction) == list(fi.idea10_expiry(d2).direction)


def test_expiry_rule_matches_real_calendar_if_data_present():
    p = fi.DATA / "nifty_expiries.csv"
    if not (p.exists() and (fi.DATA / "nifty_day_dev.csv").exists()):
        return
    d = fi.load_daily()
    real = pd.read_csv(p, parse_dates=["expiry"])["expiry"]
    real = real[real <= d["date"].max()]
    mine = set(d["date"].iloc[fi.expiry_rows(d)])
    missing = [str(x.date()) for x in real if x not in mine]
    assert not missing, missing  # every real expiry in the dev window is on my list
    extra = [str(x.date()) for x in mine if x >= real.min() and x not in set(real)]
    assert not extra, extra  # and I invent none inside the window the real list covers


# ------------------------------------------------------------------ statistics helpers
def test_bootstrap_p_extremes_and_determinism():
    rng = np.random.default_rng(1)
    strong = rng.normal(0.01, 0.002, 200)
    assert fi.bootstrap_p(strong) < 0.001
    noise = rng.normal(0.0, 0.01, 200)
    noise -= noise.mean()  # exactly zero mean -> p near 0.5
    assert 0.3 < fi.bootstrap_p(noise) < 0.7
    assert fi.bootstrap_p(strong) == fi.bootstrap_p(strong)  # fixed seed
    assert fi.bootstrap_p(np.array([])) == 1.0
    assert 0 < fi.bootstrap_p(np.array([0.01, 0.02])) <= 1.0  # fewer trades than the block size works


def test_null_p_degenerate_when_rule_trades_every_candidate():
    g = np.random.default_rng(2).normal(0.0004, 0.005, 300)
    t = fi._trades(2, "all", pd.date_range("2024-01-01", periods=300).values, np.ones(300), g, np.zeros(300, int), {0: g}, (date(2024, 1, 1), date(2024, 12, 1)))
    p, _, _ = fi.null_p(t, n_draw=500)
    approx(p, 1.0)  # null = the rule itself


def test_null_p_small_when_rule_picks_the_big_winners():
    rng = np.random.default_rng(3)
    g = rng.normal(0, 0.01, 1000)
    pick = np.argsort(g)[-100:]  # cherry-picked best 100 candidates
    t = fi._trades(0, "best", np.datetime64("2024-01-01") + np.arange(100).astype("timedelta64[D]"), np.ones(100), g[pick], np.zeros(100, int),
                   {0: g}, (date(2024, 1, 1), date(2024, 6, 1)))
    assert fi.null_p(t, n_draw=500)[0] < 0.01


def test_null_keeps_long_short_mix():
    # candidates drift up by +1% each; a rule that is 50% short has a null mean near 0 (not +1%)
    cand = np.full(400, 0.01)
    t = fi._trades(0, "mix", np.datetime64("2024-01-01") + np.arange(100).astype("timedelta64[D]"), np.r_[np.ones(50), -np.ones(50)],
                   np.full(100, 0.01), np.zeros(100, int), {0: cand}, (date(2024, 1, 1), date(2024, 6, 1)))
    _, nm, _ = fi.null_p(t, cost=0.0, n_draw=200)
    approx(nm, 0.0, 1e-12)


def test_halves_split_at_calendar_midpoint_and_empty_half_is_not_positive():
    t = fi._trades(0, "h", ["2024-01-10", "2024-01-20"], [1, 1], [0.01, 0.02], [0, 0], {0: np.array([0.01, 0.02])}, (date(2024, 1, 1), date(2024, 12, 31)))
    h = fi.halves(t, cost=0.0)
    assert h["first_n"] == 2 and h["second_n"] == 0
    r = {"n_trades": 2, "mean_net": 0.01, "boot_p": 0.0001, "null_p": 0.0001, **{k: h[k] for k in ("first_n", "second_n", "first_mean", "second_mean")}}
    v, ch = fi.verdict(r)
    assert not ch["d_both_halves_positive"] and v == "INCONCLUSIVE"


def test_verdict_mapping():
    base = dict(n_trades=100, mean_net=0.001, boot_p=0.001, null_p=0.001, first_n=50, second_n=50, first_mean=0.001, second_mean=0.002)
    assert fi.verdict(base)[0] == "SURVIVES"
    assert fi.verdict(dict(base, n_trades=59))[0] == "INCONCLUSIVE"
    assert fi.verdict(dict(base, null_p=0.2))[0] == "INCONCLUSIVE"
    assert fi.verdict(dict(base, second_mean=-0.001))[0] == "INCONCLUSIVE"
    assert fi.verdict(dict(base, boot_p=0.006))[0] == "REJECT"  # alpha is 0.005: 0.006 is not enough
    assert fi.verdict(dict(base, mean_net=-0.0001))[0] == "REJECT"
    assert fi.verdict(dict(base, boot_p=0.005))[0] == "REJECT"  # strictly below alpha


# ------------------------------------------------------------------ hygiene
def test_module_never_touches_holdout_or_orders():
    src = (HERE / "forced_trader_ideas.py").read_text().lower()
    assert ".nifty_holdout" not in src and "holdout_dir" not in src and "kite_data" not in src
    for bad in ("place_order", "placeorder", "/v2/order", "upstox_analytics_token", "api_key", "access_token"):
        assert bad not in src


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except Exception as e:  # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(e))
    print("all passed" if not fails else f"{fails} FAILED")
    sys.exit(1 if fails else 0)
