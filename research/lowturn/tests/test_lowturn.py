"""Tests for the low-turnover daily backtest. Synthetic data only (no network, no holdout).
Run:  python3 research/lowturn/tests/test_lowturn.py   (also pytest-compatible)"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # lowturn/
sys.path.insert(0, str(HERE.parents[1]))  # research/
import backtest as bt  # noqa: E402
import kite_data as kd  # noqa: E402


def _frame(opens, closes, start="2020-01-01"):
    d = pd.bdate_range(start, periods=len(closes))
    c = np.asarray(closes, float)
    o = np.asarray(opens, float)
    return pd.DataFrame({"date": d, "open": o, "high": np.maximum(o, c) * 1.001, "low": np.minimum(o, c) * 0.999, "close": c, "volume": 0})


# ---------- known answer, worked by hand ----------
def test_engine_known_answer():
    df = _frame([100, 102, 111, 99], [100, 110, 99, 100])
    w = pd.Series([1.0, 0.0, 1.0, 1.0])
    r = bt.run(df, w, cost=0.0, cash_rate=0.0)
    # day1: flat -> long at the open 102, closes 110:        110/102-1
    # day2: long overnight 110->111 (gap), sold at the open: 111/110-1
    # day3: flat overnight, long from the open 99 to 100:     100/99-1
    exp = [110 / 102 - 1, 111 / 110 - 1, 100 / 99 - 1]
    assert np.allclose(r["ret"], exp, atol=1e-12), (r["ret"].tolist(), exp)
    assert np.allclose(r["turnover"], [1, 1, 1])


def test_metrics_known_answer():
    # 5 yearly steps: wealth 1.1, 1.21, 1.089, 1.1979, 0.59895 ; span exactly 4 years (1461 days / 365.25)
    res = pd.DataFrame({"date": pd.to_datetime(["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01", "2024-01-01"]),
                        "ret": [0.1, 0.1, -0.1, 0.1, -0.5], "w": 1.0, "turnover": [1, 0, 0, 0, 0]})
    m = bt.metrics(res)
    assert abs(m["max_dd"] - (0.59895 / 1.21 - 1)) < 1e-12  # peak 1.21 (the later 1.1979 never regains it) -> trough 0.59895 = -50.5%
    assert abs(m["max_dd"] - (-0.505)) < 1e-9
    assert abs(m["cagr"] - (0.59895 ** 0.25 - 1)) < 1e-12  # = -12.03% by hand
    assert abs(m["cagr"] - (-0.12027)) < 1e-4
    assert abs(m["calmar"] - m["cagr"] / 0.505) < 1e-9
    assert abs(m["switches_per_year"] - 0.25) < 1e-12
    assert m["pct_invested"] == 1.0


def test_cash_leg_earns_6_5_percent():
    df = _frame([100] * 253, [100] * 253)
    r = bt.run(df, pd.Series(0.0, index=df.index), cost=0.0, cash_rate=0.065)
    assert abs(np.prod(1 + r["ret"].to_numpy()[:252]) - 1.065) < 1e-12


# ---------- costs ----------
def test_cost_is_charged_on_traded_value_and_ordered():
    rng = np.random.default_rng(1)
    c = 100 * np.cumprod(1 + rng.normal(0.0004, 0.01, 400))
    o = np.r_[100, c[:-1]] * (1 + rng.normal(0, 0.002, 400))
    df = _frame(o, c)
    w = bt.signal_sma(df, 20)
    base = bt.run(df, w, cost=0.0)
    res = {k: bt.run(df, w, cost=k) for k in bt.COSTS}
    for k, r in res.items():  # per-day ret differs by exactly cost * turnover
        assert np.allclose(base["ret"] - r["ret"], k * base["turnover"], atol=1e-12)
    cagr = [bt.metrics(res[k])["cagr"] for k in bt.COSTS]
    assert cagr[0] > cagr[1] > cagr[2]
    assert base["turnover"].sum() > 3  # the test signal actually trades


def test_zero_turnover_pays_no_cost():
    df = _frame(np.linspace(100, 120, 60), np.linspace(100, 120, 60))
    w = pd.Series(1.0, index=df.index)
    r0, r1 = bt.run(df, w, cost=0.0), bt.run(df, w, cost=0.005)
    assert abs((r0["ret"] - r1["ret"]).iloc[1:].abs().sum()) < 1e-15  # only the first (entry) day pays


# ---------- no lookahead ----------
def _walk(n=1500, seed=3):
    d = kd.synthetic(n, seed=seed)
    return d


def test_signals_are_causal_truncation():
    """A signal at day t must not change when later bars are removed (S1, S2, S3)."""
    df = _walk(900)
    k = 700
    for name, f in (("S1", bt.signal_sma), ("S2", bt.signal_monthly), ("S3", bt.signal_voltarget)):
        full, cut = f(df), f(df.iloc[:k].copy())
        a, b = full.iloc[: k - 1].to_numpy(), cut.iloc[: k - 1].to_numpy()  # last bar excluded: month-end needs the next bar's DATE
        assert np.allclose(a, b, equal_nan=True), name


def test_shifting_signal_changes_results():
    df = _walk()
    w = bt.signal_sma(df, 50)
    a = bt.metrics(bt.run(df, w, start=60))
    b = bt.metrics(bt.run(df, w.shift(1), start=60))
    assert abs(a["cagr"] - b["cagr"]) > 1e-4 or abs(a["max_dd"] - b["max_dd"]) > 1e-4


def test_leaky_signal_is_caught():
    """w[t] peeks at day t+1's open->close move (the move it is about to earn). It must look absurdly good, and collapse when delayed."""
    df = _walk(1500)
    peek = ((df["close"] / df["open"]).shift(-1) > 1).astype(float)
    peek.iloc[-1] = 0.0
    honest = bt.metrics(bt.run(df, bt.signal_sma(df, 50), cost=0.0025, start=60))
    bench = bt.metrics(bt.run(df, bt.signal_buyhold(df), cost=0.0025, start=60))
    leak = bt.metrics(bt.run(df, peek, cost=0.0025, start=60))
    delayed = bt.metrics(bt.run(df, peek.shift(1), cost=0.0025, start=60))
    assert leak["cagr"] > 1.0 and leak["cagr"] > 10 * max(bench["cagr"], 0.05), leak  # suspiciously good
    assert delayed["cagr"] < 0.25 * leak["cagr"], (leak, delayed)  # collapses with a one-day delay
    assert honest["cagr"] < 0.5 * leak["cagr"]


def test_decision_uses_next_open_not_same_bar():
    """Weight decided at close t must not earn day t's own return."""
    df = _frame([100, 100, 100, 100], [100, 200, 100, 100])  # day1 jumps to 200 (open 100)
    w = pd.Series([0.0, 1.0, 0.0, 0.0])  # decided AT day1's close (after the jump) -> earns nothing from the jump
    r = bt.run(df, w, cost=0.0, cash_rate=0.0, start=0)
    assert np.allclose(r["ret"].iloc[0], 0.0)  # day1: w[0]=0 -> flat through the jump


# ---------- strategy specifics ----------
def test_volatility_conversion_known_answer():
    n = 120
    lr = 0.01 * 1.595769  # E[ln(H/L)] = 1.5958 x daily sigma  -> sigma_daily = 1%
    c = np.full(n, 100.0)
    df = pd.DataFrame({"date": pd.bdate_range("2020-01-01", periods=n), "open": c, "close": c, "high": c * np.exp(lr / 2), "low": c * np.exp(-lr / 2), "volume": 0})
    w = bt.signal_voltarget(df, 0.12)
    expected = 0.12 / (0.01 * 252 ** 0.5)
    assert abs(w.iloc[-1] - expected) < 1e-3 and abs(expected - 0.75593) < 1e-4
    assert (w.dropna() <= 1.0).all()
    df2 = df.assign(high=c * np.exp(0.0005), low=c * np.exp(-0.0005))  # calm market -> capped at 1, no leverage
    assert (bt.signal_voltarget(df2, 0.12).dropna() == 1.0).all()


def test_s1_s2_signal_rules():
    c = np.r_[np.linspace(100, 200, 250), np.linspace(200, 100, 250)]
    df = _frame(c, c)
    s1 = bt.signal_sma(df, 200)
    assert s1.iloc[:199].isna().all() and s1.iloc[240] == 1.0 and s1.iloc[-1] == 0.0
    s2 = bt.signal_monthly(df, 10)
    assert s2.dropna().isin([0.0, 1.0]).all()
    changes = s2.dropna().ne(s2.dropna().shift()).iloc[1:]
    ym = df["date"].dt.year * 100 + df["date"].dt.month
    last_of_month = (ym != ym.shift(-1)).loc[changes.index]
    assert last_of_month[changes].all()  # S2 only changes on a month's last trading day (decision at that close; trades next open)


# ---------- bootstrap and tax ----------
def test_bootstrap_identical_series_has_zero_difference():
    r = np.random.default_rng(0).normal(0.0004, 0.01, 800)
    out = bt.block_bootstrap(r, r, 3.17, block=21, n=100)
    assert out["cagr_diff_90ci"] == [0.0, 0.0] and out["dd_ratio_90ci"] == [1.0, 1.0]


def _episode(days, gain):
    d = pd.to_datetime("2020-01-01") + pd.to_timedelta(np.arange(days + 1), "D")
    ret = np.zeros(days + 1)
    ret[0] = gain
    w = np.ones(days + 1)
    w[-1] = 0.0
    return pd.DataFrame({"date": d, "ret": ret, "w": w, "turnover": 0.0})


def test_after_tax_known_answers():
    st = bt.after_tax(_episode(100, 0.5))  # +500,000 in 100 days: 20% short-term
    assert abs(st["tax_st"] - 100_000) < 1e-6 and st["tax_lt"] == 0
    lt = bt.after_tax(_episode(400, 0.5))  # held > 12 months: 12.5%
    assert abs(lt["tax_lt"] - 62_500) < 1e-6 and lt["tax_st"] == 0
    lt_ex = bt.after_tax(_episode(400, 0.5), exemption=125_000)  # first Rs 1.25 lakh exempt
    assert abs(lt_ex["tax_lt"] - 46_875) < 1e-6
    assert lt["tax_drag_pp"] > 0


def test_after_tax_loss_carry_forward():
    d = pd.to_datetime("2020-01-01") + pd.to_timedelta(np.arange(6), "D")
    ret = np.array([-0.2, 0.0, 0.0, 0.5, 0.0, 0.0])  # lose 20% (-200k) then +50%
    w = np.array([1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
    out = bt.after_tax(pd.DataFrame({"date": d, "ret": ret, "w": w, "turnover": 0.0}))
    # wealth 800k after loss; second episode basis 800k -> 1.2M, gain 400k; carry-forward loss 200k -> taxable 200k -> 20% = 40k
    assert abs(out["tax_st"] - 40_000) < 1e-6, out


def test_buyhold_after_tax_is_deferred_long_term():
    res = pd.DataFrame({"date": pd.to_datetime(["2020-01-01", "2024-01-01"]), "ret": [1.0, 0.0], "w": 1.0, "turnover": 0.0})
    out = bt.after_tax_buyhold(res)
    assert abs(out["tax_lt"] - 0.125 * 1_000_000) < 1e-6  # gain 1,000,000 x 12.5%


if __name__ == "__main__":
    fails = 0
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as e:  # noqa: BLE001
            fails += 1
            print("FAIL", name, repr(e)[:300])
    print(f"{len(tests) - fails}/{len(tests)} passed")
    sys.exit(1 if fails else 0)
