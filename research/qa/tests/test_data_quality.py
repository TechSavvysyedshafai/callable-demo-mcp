"""Offline tests for research/qa/data_quality.py: clean synthetic data gives no findings; each injected defect fires its own check."""

import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
import data_quality as q

rng = np.random.default_rng(0)
DAYS = pd.bdate_range("2025-03-03", periods=6)  # Mon-Mon, no holidays


def make_bars():
    rows = []
    px = 20000.0
    for d in DAYS:
        for k in range(75):
            t = d + pd.Timedelta(hours=9, minutes=15 + 5 * k)
            o = px
            c = o * (1 + rng.normal(0, 0.0004))
            rows.append((t, o, max(o, c) * 1.0002, min(o, c) * 0.9998, c, 0))
            px = c
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])


def make_daily(bars):
    g = bars.groupby(bars["date"].dt.normalize())
    return pd.DataFrame({"date": g["open"].first().index, "open": g["open"].first().values, "high": g["high"].max().values,
                         "low": g["low"].min().values, "close": g["close"].last().values, "volume": 0})


def cats(findings):
    return {f.category: f.count for f in findings}


bars = make_bars()
daily = make_daily(bars)

# ---- clean data: silence
assert q.check_intraday(bars, daily) == [], q.report(q.check_intraday(bars, daily))
assert q.check_daily(daily) == [], q.report(q.check_daily(daily))
vix = pd.DataFrame({"date": DAYS, "close": [13.0, 13.4, 12.9, 14.1, 13.8, 13.5]})
assert q.check_vix(vix, daily, dev_cut=DAYS[-1]) == []
ex = pd.DataFrame({"expiry": ["2025-03-04", "2025-03-11", "2025-03-18", "2025-03-25"]})  # four Tuesdays, 7 days apart
assert q.check_expiries(ex, None, None, pd.Timestamp("2025-04-01")) == []

# ---- intraday defects
b = bars.copy(); b.loc[5, "close"] = np.nan
assert cats(q.check_intraday(b))["nan"] == 1
b = pd.concat([bars, bars.iloc[[10]]]).sort_values("date", kind="stable")
assert cats(q.check_intraday(b))["duplicate_timestamp"] == 1
b = bars.iloc[::-1].reset_index(drop=True)
assert cats(q.check_intraday(b))["unsorted"] >= 1
b = bars.copy(); b.loc[7, "open"] = -5.0
assert cats(q.check_intraday(b))["nonpositive_price"] == 1
b = bars.copy(); b.loc[8, ["high", "low"]] = [b.loc[8, "low"] - 1, b.loc[8, "high"]]
assert cats(q.check_intraday(b))["high_below_low"] == 1
b = bars.copy(); b.loc[9, "close"] = b.loc[9, "high"] + 50
assert cats(q.check_intraday(b))["ohlc_outside_range"] == 1
b = bars.copy(); b.loc[11, "date"] = b.loc[11, "date"].normalize() + pd.Timedelta(hours=18, minutes=15)  # a bar at 18:15
c = cats(q.check_intraday(b))
assert c["outside_session_hours"] == 1
b = bars.copy(); b["date"] = b["date"].dt.tz_localize("Asia/Kolkata")
assert cats(q.check_intraday(b))["timezone"] == len(b)
b = bars.drop(bars.index[100:104]).reset_index(drop=True)  # 4 bars removed inside one session
c = cats(q.check_intraday(b))
assert c["intraday_gap"] == 1 and c["missing_bars_in_gaps"] == 4 and c["short_day"] == 1, c
b = bars[bars["date"].dt.normalize() != DAYS[2]]  # an entire day missing vs the daily file
assert cats(q.check_intraday(b, daily))["missing_day_vs_daily"] == 1
sat = bars.copy(); sat.loc[sat["date"].dt.normalize() == DAYS[1], "date"] += pd.Timedelta(days=5 - DAYS[1].dayofweek)
assert "weekend_days" in cats(q.check_intraday(sat))
b = bars.copy(); b.loc[200, ["open", "high", "low", "close"]] = [20000, 21500, 20000, 21500]  # +7% in one bar
b.loc[201, ["open", "high", "low", "close"]] = [21500, 21500, 20000, 20000]
f = cats(q.check_intraday(b, make_daily(bars)))  # daily bar from the CLEAN bars does not contain the spike
assert f["outlier_5sigma"] >= 1 and f["outlier_unconfirmed"] >= 1 and f["outlier_reverting"] >= 1, f
assert len(b) == len(bars)  # nothing was dropped
d2 = daily.copy(); d2.loc[3, "close"] *= 1.01
assert cats(q.check_intraday(bars, d2))["vs_daily_close"] == 1
d2 = daily.copy(); d2.loc[2, "high"] *= 1.02
assert cats(q.check_intraday(bars, d2))["vs_daily_high"] == 1

# ---- daily defects
d = daily.copy(); d.loc[1, "low"] = d.loc[1, "high"] + 1
assert cats(q.check_daily(d))["high_below_low"] == 1
d = daily.copy(); d.loc[1, "date"] = pd.Timestamp("2025-03-08")  # a Saturday
assert "weekend_days" in cats(q.check_daily(d))
d = daily.drop(daily.index[2:4]).reset_index(drop=True); d.loc[2:, "date"] += pd.Timedelta(days=4)
assert "calendar_gap_over_4d" in cats(q.check_daily(d))
many = pd.DataFrame({"date": pd.bdate_range("2022-01-03", periods=520)})
px = 100 * np.exp(np.cumsum(rng.normal(0, 0.005, 520))); many["close"] = px; many["open"] = px; many["high"] = px * 1.001; many["low"] = px * 0.999
many.loc[300, "close"] *= 1.5
many.loc[300, "high"] = many.loc[300, "close"]
many.loc[301:, ["open", "high", "low", "close"]] *= 1.5
assert cats(q.check_daily(many))["outlier_5sigma"] >= 1

# ---- vix defects
v = vix.copy(); v.loc[2, "close"] = 0
c = cats(q.check_vix(v, daily)); assert c["nonpositive_price"] == 1 and c["implausible_level"] == 1
v = vix.copy(); v.loc[1, "close"] = np.nan
assert cats(q.check_vix(v))["nan"] == 1
v = pd.concat([vix, vix.iloc[[0]]]); assert cats(q.check_vix(v))["duplicate_timestamp"] == 1
v = vix.drop(vix.index[2]); assert cats(q.check_vix(v, daily))  # no crash; date_in_daily_not_in_vix only counts inside the VIX span
v = vix.copy(); v.loc[5, "date"] = pd.Timestamp("2025-03-08")  # Saturday, and not a NIFTY day
c = cats(q.check_vix(v, daily)); assert c["weekend_days"] == 1 and c["date_in_vix_not_in_daily"] == 1, c
assert cats(q.check_vix(vix, daily, dev_cut=DAYS[2]))["beyond_dev_cutoff"] == 3
v = pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=40), "close": 13.0})
assert cats(q.check_vix(v))["stale_value"] == 1
v = pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=60), "close": 13 + rng.normal(0, 0.1, 60)}); v.loc[30, "close"] = 40
assert cats(q.check_vix(v))["outlier_5sigma"] >= 1

# ---- expiry defects
e = pd.DataFrame({"expiry": ["2025-03-04", "2025-03-11", "2025-03-19", "2025-03-27"]})  # 7, 8, 8 day gaps and Tue->Wed->Thu
c = cats(q.check_expiries(e)); assert c["gap_not_7_days"] == 2 and c["weekday_changes"] == 2, c
e = pd.DataFrame({"expiry": ["2025-03-04", "2025-03-04", "2025-03-11"]}); assert cats(q.check_expiries(e))["duplicate_timestamp"] == 1
e = pd.DataFrame({"expiry": ["2025-03-11", "2025-03-04"]}); assert cats(q.check_expiries(e))["unsorted"] == 1
e = pd.DataFrame({"expiry": ["2025-03-08", "2025-03-11"]}); assert cats(q.check_expiries(e))["weekend_expiry"] == 1
e = pd.DataFrame({"expiry": ["2025-03-04", "not-a-date"]}); assert cats(q.check_expiries(e))["unparseable"] == 1
e = pd.DataFrame({"expiry": ["2025-03-04", "2025-03-09"]})  # Sunday: not a trading day in the daily file
assert cats(q.check_expiries(e, daily))["expiry_not_a_trading_day"] == 1
e = pd.DataFrame({"expiry": ["2025-03-04", "2025-03-11", "2026-01-06"]})
c = cats(q.check_expiries(e, daily, dev_cut=DAYS[-1], today=pd.Timestamp("2025-04-01")))
assert c["future_expiry"] == 1 and c["beyond_dev_cutoff"] >= 1 and c["expiry_beyond_daily_data"] == 2, c
e = pd.DataFrame({"expiry": ["2025-03-04"]}); d_no = daily[daily["date"] != pd.Timestamp("2025-03-04")]
assert cats(q.check_expiries(e, d_no))["expiry_not_a_trading_day"] == 1

# ---- option files
def opt_df(day, n=75, vol=100, oi=1000):
    t = [day + pd.Timedelta(hours=9, minutes=15 + 5 * k) for k in range(n)]
    p = 100 + np.cumsum(rng.normal(0, 0.2, n))
    return pd.DataFrame({"date": t, "open": p, "high": p + 0.3, "low": p - 0.3, "close": p, "volume": vol, "oi": oi})


assert q.check_option_file(opt_df(DAYS[0]), "x") == []
o = opt_df(DAYS[0]); o.loc[3, "volume"] = -4; o.loc[4, "oi"] = np.nan
c = cats(q.check_option_file(o, "x")); assert c["negative_volume"] == 1 and c["nan_oi"] == 1, c
o = opt_df(DAYS[0], vol=0); o["high"] = o["low"] = o["close"] = o["open"]
c = cats(q.check_option_file(o, "x")); assert c["zero_volume_flat_bar"] == 75 and c["zero_volume_bar"] == 75
o = opt_df(DAYS[0]); o.loc[0, "low"] = o.loc[0, "high"] + 1
assert cats(q.check_option_file(o, "x"))["high_below_low"] == 1

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    exp = DAYS[2]  # 2025-03-05
    # spot sits near 20000-ish; save only strikes far from spot for the CE side and a different set for the PE side
    spot_close = float(bars.loc[bars["date"].dt.normalize() == exp, "close"].median())
    atm = int(round(spot_close / 50) * 50)
    for strike in (atm - 100, atm, atm + 100):
        opt_df(DAYS[1]).assign(oi=1000).to_csv(tmp / f"{exp:%Y-%m-%d}_{strike}CE.csv", index=False)
    opt_df(DAYS[1]).to_csv(tmp / f"{exp:%Y-%m-%d}_{atm}PE.csv", index=False)  # PE has 1 strike, CE has 3
    far = opt_df(DAYS[1]); far.loc[10, "oi"] = 10_000_000; far.loc[11, "volume"] = 1_000_000
    far.to_csv(tmp / f"{exp:%Y-%m-%d}_{atm + 100}PE.csv", index=False)
    (tmp / "junk.csv").write_text("a,b\n1,2\n")
    ghost = opt_df(exp + pd.Timedelta(days=1)); ghost.to_csv(tmp / f"{exp:%Y-%m-%d}_{atm - 150}PE.csv", index=False)  # rows after expiry
    f, st = q.check_options(tmp, bars, daily)
    c = cats(f)
    assert c["unparseable_filename"] == 1 and c["strike_asymmetry"] >= 1, c
    assert c["oi_jump"] == 1 and c["volume_spike"] == 1 and c["rows_after_expiry_date"] == 75, c
    assert st["files"] == 6 and st["expiries"] == 1
    # strike coverage: the data's spot (~20000) lies far from strikes saved around a far-away ATM
    for p in tmp.glob("2025*.csv"):
        p.unlink()
    for strike in (30000, 30050):
        opt_df(DAYS[1]).to_csv(tmp / f"{exp:%Y-%m-%d}_{strike}CE.csv", index=False)
    f, st = q.check_options(tmp, bars, daily)
    assert cats(f)["spot_outside_saved_strikes"] > 0, cats(f)
    # a gappy file: 50 of 75 bars on its one day
    for p in tmp.glob("2025*.csv"):
        p.unlink()
    opt_df(DAYS[1], n=50).to_csv(tmp / f"{exp:%Y-%m-%d}_{atm}CE.csv", index=False)
    f, st = q.check_options(tmp, bars, daily)
    assert cats(f)["candle_coverage_gap"] == 25, cats(f)

print("data quality tests ok")
