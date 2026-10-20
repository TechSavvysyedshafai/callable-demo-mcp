"""Task 12 (crowd positioning on crypto perpetuals, B7-01) self-checks: hand-computed z-score (only PRIOR days, window 90, minimum 60), signal-row choice (the 23:50 row,
duplicates collapsed), trade timing (signal day D -> entry open D+1, exit open D+2), payoff signs for long / short, cost arithmetic, skip accounting, no lookahead
(data after day D cannot change the day-D signal), thresholds, overlap rule, drawdown, holdout guards. Synthetic data only; no market files needed.
Run:  python research/crypto/tests/test_crypto_b7.py   (also collected by pytest)."""

import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import crypto_core as cc  # noqa: E402
import crypto_fetch as cf  # noqa: E402


def approx(a, b, tol=1e-9):
    assert abs(a - b) <= tol, (a, b)


def xs(values, start="2024-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


# ----------------------------------------------------------------------------------------------- z-score
def test_z_hand_computed():
    # 60 prior values 1..60 then day 61 has x = 100. mean(1..60) = 30.5; sample sd = sqrt(60*61/12) = sqrt(305) (ddof 1 variance of 1..n = n(n+1)/12)
    x = xs(list(range(1, 61)) + [100])
    z = cc.zscores(x)
    approx(z["z"].iloc[60], (100 - 30.5) / np.sqrt(60 * 61 / 12))
    assert z["status"].iloc[60] == "ok"
    assert z["status"].iloc[59] == "lt60_history" and np.isnan(z["z"].iloc[59])  # only 59 prior values


def test_z_window_is_last_90_prior_values_only():
    vals = [1000.0] * 10 + list(np.arange(1, 91, dtype=float)) + [50.0]  # 101 prior values; the 10 huge ones are older than 90 days
    z = cc.zscores(xs(vals))
    last = np.arange(1, 91, dtype=float)
    approx(z["z"].iloc[100], (50 - last.mean()) / last.std(ddof=1))


def test_z_uses_only_prior_days_and_not_day_d():
    base = list(np.sin(np.arange(80)) + 5)
    a = xs(base + [3.0] + [9.0] * 5)
    b = xs(base + [3.0] + [-4.0, 7.0, 1.0, 2.0, 8.0])  # everything AFTER day 80 differs
    za, zb = cc.zscores(a), cc.zscores(b)
    approx(za["z"].iloc[80], zb["z"].iloc[80])
    c = xs(base + [99.0])  # day D's own value differs: the window must not contain it, so its z uses the same 80 prior values
    m, s = np.mean(base[-90:]), np.std(base[-90:], ddof=1)
    approx(cc.zscores(c)["z"].iloc[80], (99 - m) / s)


def test_z_missing_days_do_not_shorten_window():
    v = list(np.arange(1, 71, dtype=float))
    x = xs(v + [np.nan, np.nan, 5.0])  # two missing days before the last day
    z = cc.zscores(x)
    assert z["status"].iloc[70] == "no_x" and z["status"].iloc[71] == "no_x"
    approx(z["z"].iloc[72], (5 - np.mean(v)) / np.std(v, ddof=1))
    assert z["span_days"].iloc[72] == 72  # calendar span of the 70 values used: first value is day 0, D is day 72


def test_z_zero_sd_is_skipped():
    z = cc.zscores(xs([1.0] * 61))
    assert z["status"].iloc[60] == "zero_sd" and np.isnan(z["z"].iloc[60])


# ----------------------------------------------------------------------------------------------- signal row
def day_frame(day="2024-03-05", ratio_2350=1.5, extra=True, dup=True, conflict=False):
    ts = pd.date_range(f"{day} 00:00", periods=288, freq="5min")
    df = pd.DataFrame({"create_time": ts.strftime("%Y-%m-%d %H:%M:%S"), "count_long_short_ratio": 1.0, "count_toptrader_long_short_ratio": 2.0})
    df.loc[df["create_time"] == f"{day} 23:50:00", "count_long_short_ratio"] = ratio_2350
    df.loc[df["create_time"] == f"{day} 23:55:00", "count_long_short_ratio"] = 9.0  # the row after: must never be used
    df.loc[df["create_time"] == f"{day} 00:00:00", "count_long_short_ratio"] = 7.0
    if dup:
        d = df.copy()
        if conflict:
            d.loc[d["create_time"] == f"{day} 10:00:00", "count_long_short_ratio"] = 123.0
        df = pd.concat([df, d]).sort_values("create_time", kind="stable").reset_index(drop=True)
    return df


def test_signal_row_is_2350_and_duplicates_collapse():
    clean, qa = cc.clean_day(day_frame())
    assert qa["raw_rows"] == 576 and qa["unique_rows"] == 288 and qa["dup_rows"] == 288 and qa["dup_conflicts"] == 0
    v, why = cc.signal_row(clean, date(2024, 3, 5), "count_long_short_ratio")
    assert v == 1.5 and why is None  # not the 23:55 value (9.0), not the 00:00 value (7.0)
    t, _ = cc.signal_row(clean, date(2024, 3, 5), "count_toptrader_long_short_ratio")
    assert t == 2.0
    q = cc.day_qa(clean, date(2024, 3, 5))
    assert q["full_day"] and q["first"] == "00:00:00" and q["last"] == "23:55:00"


def test_duplicate_conflicts_are_counted_and_first_row_wins():
    clean, qa = cc.clean_day(day_frame(conflict=True))
    assert qa["dup_conflicts"] == 1
    row = clean[clean["create_time"] == pd.Timestamp("2024-03-05 10:00:00")].iloc[0]
    assert row["count_long_short_ratio"] == 1.0  # the first of the two, not 123


def test_missing_2350_row_and_bad_ratio_are_skipped_with_a_reason():
    df = day_frame(dup=False)
    gone = df[df["create_time"] != "2024-03-05 23:50:00"]
    clean, _ = cc.clean_day(gone)
    v, why = cc.signal_row(clean, date(2024, 3, 5), "count_long_short_ratio")
    assert v is None and why == "no_2350_row"
    assert not cc.day_qa(clean, date(2024, 3, 5))["full_day"]
    for bad in (0.0, -1.0, float("nan")):
        clean, _ = cc.clean_day(day_frame(ratio_2350=bad, dup=False))
        v, why = cc.signal_row(clean, date(2024, 3, 5), "count_long_short_ratio")
        assert v is None and why == "bad_ratio"


def test_off_day_stamps_are_flagged_as_a_timezone_problem():
    df = day_frame(dup=False)
    shifted = df.copy()
    shifted["create_time"] = (pd.to_datetime(shifted["create_time"]) + pd.Timedelta(hours=5, minutes=30)).dt.strftime("%Y-%m-%d %H:%M:%S")
    clean, _ = cc.clean_day(shifted)
    q = cc.day_qa(clean, date(2024, 3, 5))
    assert q["off_day"] > 0 and not q["full_day"]


# ----------------------------------------------------------------------------------------------- direction and trades
def test_direction_and_threshold_edges():
    assert cc.direction(1.5) == -1 and cc.direction(1.5 - 1e-13) == -1 and cc.direction(1.4999) == 0  # crowd long -> SHORT
    assert cc.direction(-1.5) == 1 and cc.direction(-1.4999) == 0  # crowd short -> LONG
    assert cc.direction(0.0) == 0 and cc.direction(float("nan")) == 0
    assert cc.direction(1.0, 1.0) == -1 and cc.direction(-2.0, 2.0) == 1


def synth(n=70, spike_day=65, spike=3.0, start="2024-01-01"):
    """x is a gentle alternation (sd ~ 0.05) with one big spike on `spike_day`; daily opens = 100 + day index so prices are easy to check by hand."""
    idx = pd.date_range(start, periods=n + 10, freq="D")
    x = pd.Series(np.where(np.arange(n + 10) % 2 == 0, 0.05, -0.05), index=idx)
    if spike_day is not None:
        x.iloc[spike_day] = spike
    opens = pd.Series(100.0 + np.arange(n + 10), index=idx)
    return x, opens


def test_trade_timing_signs_and_cost():
    x, opens = synth(spike=3.0)  # crowd heavily long on day 65 -> SHORT
    z = cc.zscores(x)
    run = cc.build_trades(z, opens, date(2024, 1, 1), last_day=date(2024, 3, 31))
    t = run.trades
    assert len(t) == 1
    r = t.iloc[0]
    d = pd.Timestamp("2024-01-01") + pd.Timedelta(days=65)
    assert r["signal_date"] == d and r["direction"] == -1
    assert r["entry"] == d + pd.Timedelta(days=1) and r["exit"] == d + pd.Timedelta(days=2)
    entry_px, exit_px = 100.0 + 66, 100.0 + 67  # the OPEN of D+1 and of D+2 (prices rise 1 per day)
    approx(r["gross"], exit_px / entry_px - 1)
    approx(r["net"], -1 * (exit_px / entry_px - 1) - 0.0012)  # short loses when price rises, then pays 0.12%
    approx(r["net_zero_cost"], -(exit_px / entry_px - 1))
    # crowd heavily SHORT -> LONG, which wins when price rises
    x2, _ = synth(spike=-3.0)
    run2 = cc.build_trades(cc.zscores(x2), opens, date(2024, 1, 1), last_day=date(2024, 3, 31))
    r2 = run2.trades.iloc[0]
    assert r2["direction"] == 1
    approx(r2["net"], (exit_px / entry_px - 1) - 0.0012)
    assert r2["net"] > 0 > r["net"]
    # sign flip (follow-the-crowd) is exactly the mirror image before costs
    run3 = cc.build_trades(z, opens, date(2024, 1, 1), last_day=date(2024, 3, 31), sign=-1)
    approx(run3.trades.iloc[0]["net_zero_cost"], -r["net_zero_cost"])


def test_exit_price_is_the_open_after_entry_not_the_close_or_the_signal_day():
    x, opens = synth(spike=3.0)
    opens = opens.copy()
    d = pd.Timestamp("2024-01-01") + pd.Timedelta(days=65)
    opens.loc[d] = 1.0  # the signal day's own bar: must not matter
    opens.loc[d + pd.Timedelta(days=3)] = 1.0  # a later bar: must not matter
    run = cc.build_trades(cc.zscores(x), opens, date(2024, 1, 1), last_day=date(2024, 3, 31))
    approx(run.trades.iloc[0]["gross"], 167.0 / 166.0 - 1)


def test_skip_accounting_adds_up():
    x, opens = synth(spike=3.0)
    x = x.copy()
    x.iloc[62] = np.nan  # a day with no 23:50 row
    z = cc.zscores(x)
    drop = pd.Timestamp("2024-01-01") + pd.Timedelta(days=66)
    opens2 = opens.drop(pd.Timestamp("2024-01-01") + pd.Timedelta(days=67))  # exit bar missing for the day-65 signal
    run = cc.build_trades(z, opens2, date(2024, 1, 1), last_day=date(2024, 3, 31))
    sc = cc.skip_counts(run)
    assert sum(sc.values()) == len(pd.date_range("2024-01-01", "2024-03-31"))  # every calendar day has exactly one status
    assert sc["no_x"] == 1
    assert sc["no_price"] >= 1 and len(run.trades) == 0  # the spike signal could not be priced: skipped, counted, not replaced
    assert sc["lt60_history"] == 60 - 0 - 0 or sc["lt60_history"] >= 59  # first 60 days (one may be the missing x)
    assert sc.get("no_file", 0) == (pd.Timestamp("2024-03-31") - x.index[-1]).days  # days after the last file


def test_exit_after_dev_end_is_a_skip_not_a_holdout_price():
    x, opens = synth(spike=3.0)
    last = pd.Timestamp("2024-01-01") + pd.Timedelta(days=66)  # signal day 65, exit day 67 is after "last_day"
    run = cc.build_trades(cc.zscores(x), opens, date(2024, 1, 1), last_day=last.date())
    assert len(run.trades) == 0 and cc.skip_counts(run)["no_price"] == 2  # day 65 (exit day 67) and day 66 (exit day 68)


def test_overlap_rule_for_longer_holds_but_not_for_24h():
    x, opens = synth(spike=3.0)
    x = x.copy()
    x.iloc[66] = -4.0  # signals on consecutive days 65 (short) and 66 (long)
    z = cc.zscores(x)
    r1 = cc.build_trades(z, opens, date(2024, 1, 1), last_day=date(2024, 3, 31))
    assert len(r1.trades) == 2  # 24h holds chain: exit of trade 1 == entry of trade 2
    r3 = cc.build_trades(z, opens, date(2024, 1, 1), hold=timedelta(days=3), last_day=date(2024, 3, 31))
    assert len(r3.trades) == 1 and cc.skip_counts(r3)["overlap"] == 1


def test_four_hour_hold_uses_hourly_opens():
    x, _ = synth(spike=3.0)
    hours = pd.date_range("2024-01-01", periods=24 * 80, freq="h")
    hourly = pd.Series(100.0 + np.arange(len(hours)) / 24.0, index=hours)
    run = cc.build_trades(cc.zscores(x), hourly, date(2024, 1, 1), hold=timedelta(hours=4), last_day=date(2024, 3, 31))
    r = run.trades.iloc[0]
    assert r["exit"] - r["entry"] == pd.Timedelta(hours=4)
    approx(r["gross"], hourly[r["exit"]] / hourly[r["entry"]] - 1)


# ----------------------------------------------------------------------------------------------- no lookahead
def test_no_lookahead_signal_and_earlier_trades_ignore_later_data():
    rng = np.random.default_rng(1)
    n = 200
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    x = pd.Series(rng.normal(0, 1, n), index=idx)
    opens = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)), index=idx)
    D = 150
    z0 = cc.zscores(x)
    run0 = cc.build_trades(z0, opens, date(2024, 1, 1), last_day=idx[-1].date())
    x2, o2 = x.copy(), opens.copy()
    x2.iloc[D + 1:] = rng.normal(5, 3, n - D - 1)  # everything after day D changes
    o2.iloc[D + 3:] = rng.normal(500, 50, n - D - 3)  # and prices after D+2
    z1 = cc.zscores(x2)
    assert np.allclose(z0["z"].iloc[:D + 1].to_numpy(), z1["z"].iloc[:D + 1].to_numpy(), equal_nan=True)  # day-D signal and all earlier ones unchanged
    run1 = cc.build_trades(z1, o2, date(2024, 1, 1), last_day=idx[-1].date())
    cut = idx[D]
    a, b = run0.trades[run0.trades.signal_date <= cut], run1.trades[run1.trades.signal_date <= cut]
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))
    # and the day-D z itself uses nothing from day D's future even through the signal-row loader: only the 23:50 stamp of day D is read
    clean, _ = cc.clean_day(day_frame(ratio_2350=1.5))
    clean2 = clean.copy()
    clean2.loc[clean2["create_time"] > pd.Timestamp("2024-03-05 23:50:00"), "count_long_short_ratio"] = 77.0  # the 23:55 row differs
    assert cc.signal_row(clean, date(2024, 3, 5), "count_long_short_ratio")[0] == cc.signal_row(clean2, date(2024, 3, 5), "count_long_short_ratio")[0]


# ----------------------------------------------------------------------------------------------- statistics helpers
def test_max_drawdown_hand_computed():
    # cumulative: 0.01, 0.03, -0.01, 0.00, 0.05 ... peak 0.03 -> trough -0.01 = 0.04
    approx(cc.max_drawdown([0.01, 0.02, -0.04, 0.01, 0.05]), 0.04)
    approx(cc.max_drawdown([-0.01, -0.02]), 0.03)  # a start straight into losses counts from 0
    approx(cc.max_drawdown([0.01, 0.01]), 0.0)


def test_stats_and_by_year_arithmetic():
    x, opens = synth(spike=3.0)
    run = cc.build_trades(cc.zscores(x), opens, date(2024, 1, 1), last_day=date(2024, 3, 31))
    s = cc.stats(run, with_null=False)
    assert s["n_trades"] == 1 and s["n_short"] == 1 and s["n_long"] == 0
    approx(s["mean_net"], -(167 / 166 - 1) - 0.0012)
    approx(s["mean_zero_cost"], -(167 / 166 - 1))
    yr = cc.by_year(run)
    assert yr[0]["year"] == 2024 and yr[0]["n"] == 1
    approx(yr[0]["total_net"], s["mean_net"])


def test_null_pool_is_every_eligible_day():
    x, opens = synth(spike=3.0)
    run = cc.build_trades(cc.zscores(x), opens, date(2024, 1, 1), last_day=date(2024, 3, 31))
    sc = cc.skip_counts(run)
    assert len(run.pool) == sc["flat"] + sc["traded"] + sc.get("overlap", 0)  # days with a z AND both prices


# ----------------------------------------------------------------------------------------------- holdout / hygiene
def test_fetcher_never_allows_holdout_files():
    ok = "data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2025-12-31.zip"
    bad = "data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2026-01-01.zip"
    assert cf.allowed(ok) and not cf.allowed(bad)
    assert cf.allowed("data/futures/um/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2025-12.zip")
    assert not cf.allowed("data/futures/um/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2026-01.zip")
    assert not cf.allowed("data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2027-06-30.zip")
    try:
        cf.fetch(bad, "metrics", "BTCUSDT", {"have": 0, "saved": 0, "missing": []})
    except AssertionError:
        pass
    else:
        raise AssertionError("fetch() requested a holdout file")


def test_loaders_refuse_holdout_data(tmp_path=None):
    import tempfile
    d = Path(tempfile.mkdtemp())
    (d / "BTCUSDT-metrics-2026-01-01.csv").write_text("create_time,symbol\n2026-01-01 00:00:00,BTCUSDT\n")
    try:
        cc.load_signal_columns("BTCUSDT", base=d)
    except RuntimeError:
        pass
    else:
        raise AssertionError("metrics loader read a 2026 file")
    k = Path(tempfile.mkdtemp())
    ms = int(pd.Timestamp("2026-01-01").timestamp() * 1000)
    (k / "BTCUSDT-1d-2026-01.csv").write_text(f"open_time,open,high,low,close,volume\n{ms},1,1,1,1,1\n")
    try:
        cc.load_opens("BTCUSDT", base=k)
    except RuntimeError:
        pass
    else:
        raise AssertionError("kline loader accepted a 2026 bar")


def test_kline_reader_handles_header_and_microseconds():
    import tempfile
    d = Path(tempfile.mkdtemp())
    ms = int(pd.Timestamp("2024-05-01").timestamp() * 1000)
    (d / "a.csv").write_text(f"open_time,open,high,low,close\n{ms},10.5,11,10,10.7\n{ms + 86400000},10.7,12,10,11\n")
    (d / "b.csv").write_text(f"{ms * 1000 + 2 * 86400 * 10**6},12.5,13,12,12.7\n")  # no header, microsecond stamps
    s = cc.load_opens("X", base=d)
    assert list(s.index) == [pd.Timestamp("2024-05-01"), pd.Timestamp("2024-05-02"), pd.Timestamp("2024-05-03")] and list(s.values) == [10.5, 10.7, 12.5]


def test_no_order_code_and_no_secrets_in_crypto_modules():
    bad_words = ("create_order", "new_order", "place_order", "placeorder", "api_key", "apikey", "secret", "signature", "x-mbx-apikey")
    for f in HERE.glob("*.py"):
        low = f.read_text().lower()
        for w in bad_words:
            assert w not in low, (f.name, w)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"{len(fns)} tests passed")
