"""Task 10 (crowd positioning, B5-01) self-checks: hand-computed PCR and z-score, expanding window uses only earlier weeks, no lookahead (signal only
from candles at or before 09:25), skipped-week accounting, payoff signs and cost, entry-day timing, thresholds, halves, verdict mapping, file hygiene.
No market data files needed (synthetic candles).
Run:  python research/crowd/tests/test_crowd.py   (also collected by pytest)."""

import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import crowd_core as cc  # noqa: E402

T925 = pd.Timestamp("2025-01-03 09:25")


def approx(a, b, tol=1e-9):
    assert abs(a - b) <= tol, (a, b)


def leg(oi_at_925, *, extra_after=None, nan=False):
    """One option file: bars 09:15..09:35 with the given OI at 09:25 (and optionally a different OI after it)."""
    ts = pd.date_range("2025-01-03 09:15", periods=5, freq="5min")
    oi = [1.0, 1.0, np.nan if nan else float(oi_at_925), extra_after if extra_after is not None else 7.0, extra_after if extra_after is not None else 7.0]
    return pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1, "oi": oi}, index=pd.DatetimeIndex(ts, name="date"))


def loader_from(table):
    """table {(strike, kind): DataFrame}; expiry ignored."""
    return lambda ex, k, kind: table.get((int(k), kind))


def plan(k=0, spot=25010.0, skipped=None, expiry=date(2025, 1, 9)):
    return {"k": k, "expiry": expiry, "entry_day": date(2025, 1, 3), "sig_ts": T925, "spot": spot, "skipped": skipped}


# ----------------------------------------------------------------------------------------------- PCR
def test_round50_and_grid():
    assert cc.round50(24975.0) == 25000  # halves up
    assert cc.round50(24974.9) == 24950
    assert cc.round50(25010.0) == 25000
    g = cc.strike_grid(25010.0)
    assert g == [24750 + 50 * i for i in range(11)] and len(g) == 11


def test_pcr_hand_computed_and_strike_filters():
    S = 25010.0  # window |K-S| <= 250 -> 24800 .. 25250 (24750 is 260 away); 25250 is 240 away
    tbl = {}
    calls = {24800: 100, 24850: 200, 24900: 300, 24950: 400, 25000: 500, 25050: 600, 25100: 700, 25150: 800, 25200: 900, 25250: 1000}
    puts = {24800: 1000, 24850: 900, 24900: 800, 24950: 700, 25000: 600, 25050: 500, 25100: 400, 25150: 300, 25200: 200, 25250: 100}
    for k in calls:
        tbl[(k, "CE")] = leg(calls[k])
        tbl[(k, "PE")] = leg(puts[k])
    tbl[(24750, "CE")] = leg(5e6)  # outside the window: ignored
    tbl[(24750, "PE")] = leg(5e6)
    r = cc.pcr_of_week(plan(spot=S), loader_from(tbl))
    assert r["n_strikes"] == 10 and r["call_oi"] == 5500 and r["put_oi"] == 5500
    approx(r["pcr"], 1.0)
    approx(r["x"], 0.0)
    # remove: a put file (24800), a call candle at 09:25 (24850 call -> NaN oi), a whole call file (24900): those three strikes drop out of BOTH sums
    del tbl[(24800, "PE")]
    tbl[(24850, "CE")] = leg(200, nan=True)
    del tbl[(24900, "CE")]
    r = cc.pcr_of_week(plan(spot=S), loader_from(tbl))
    assert r["n_strikes"] == 7
    c = 400 + 500 + 600 + 700 + 800 + 900 + 1000
    p = 700 + 600 + 500 + 400 + 300 + 200 + 100
    assert r["call_oi"] == c and r["put_oi"] == p
    approx(r["x"], math.log(p / c))
    # narrower window +/-150: |K-S| <= 150 -> 24900..25150; the 24900 call is gone, so 24950..25150 = 5 strikes
    r150 = cc.pcr_of_week(plan(spot=S), loader_from(tbl), half=150)
    assert r150["n_strikes"] == 5
    assert r150["call_oi"] == 400 + 500 + 600 + 700 + 800 and r150["put_oi"] == 700 + 600 + 500 + 400 + 300


def test_zero_oi_side_and_no_strike_are_skipped():
    tbl = {(25000, "CE"): leg(0.0), (25000, "PE"): leg(50.0)}
    r = cc.pcr_of_week(plan(), loader_from(tbl))
    assert r["x"] is None and r["skipped"] == "zero_oi_side"
    r = cc.pcr_of_week(plan(), loader_from({}))
    assert r["x"] is None and r["skipped"] == "no_oi_at_signal" and r["n_strikes"] == 0
    r = cc.pcr_of_week(plan(skipped="no_0925_bar"), loader_from(tbl))
    assert r["x"] is None and r["skipped"] == "no_0925_bar"


# ----------------------------------------------------------------------------------------------- z-score
def test_zscore_hand_computed():
    hist = list(range(1, 21))  # 1..20: mean 10.5, sample sd = sqrt(665/19)
    sd = math.sqrt(665 / 19)
    z, why = cc.zscore(hist, 20.0)
    assert why is None
    approx(z, (20 - 10.5) / sd)
    assert cc.zscore(list(range(1, 20)), 3.0) == (None, "lt20_history")  # 19 prior values
    assert cc.zscore([1.0] * 25, 2.0) == (None, "zero_sd")


def test_zscore_window_is_expanding_then_capped_at_52():
    hist = [0.0] * 8 + [float(i) for i in range(60)]  # 68 values
    z, _ = cc.zscore(hist, 10.0)
    last52 = np.array(hist[-52:])
    approx(z, (10.0 - last52.mean()) / last52.std(ddof=1))
    h30 = hist[:30]  # fewer than 52: uses all 30
    z30, _ = cc.zscore(h30, 10.0)
    a = np.array(h30)
    approx(z30, (10.0 - a.mean()) / a.std(ddof=1))


def synthetic_weeks(xs, call=1_000_000.0):
    """One plan per x with a single strike (25000) whose put/call OI gives ln(PCR) = x at 09:25."""
    plans, tbls = [], []
    for k, x in enumerate(xs):
        plans.append(plan(k=k, expiry=date(2025, 1, 9) + timedelta(days=7 * k)))
        tbls.append({(25000, "CE"): leg(call), (25000, "PE"): leg(call * math.exp(x))})
    ex_to = {p["expiry"]: t for p, t in zip(plans, tbls)}
    return plans, (lambda ex, k, kind: ex_to[ex].get((int(k), kind)))


def test_expanding_window_uses_only_earlier_weeks():
    rng = np.random.default_rng(1)
    xs = list(rng.normal(0, 0.3, 40))
    plans, ld = synthetic_weeks(xs)
    base = cc.signal_weeks(plans, ld)
    assert all(r["z"] is None and r["skipped"] == "lt20_history" for r in base[:20])  # weeks 0..19 have < 20 prior
    assert base[20]["z"] is not None
    # week 20's z from its 20 earlier x only (hand recomputation)
    a = np.array(xs[:20])
    approx(base[20]["z"], (xs[20] - a.mean()) / a.std(ddof=1), 1e-9)
    # change a LATER week (30): every z for weeks <= 29 is unchanged
    xs2 = list(xs)
    xs2[30] += 5.0
    plans2, ld2 = synthetic_weeks(xs2)
    alt = cc.signal_weeks(plans2, ld2)
    for k in range(30):
        assert base[k]["z"] == alt[k]["z"] or (base[k]["z"] is None and alt[k]["z"] is None)
    assert base[31]["z"] != alt[31]["z"]  # and it does feed later weeks
    # a week's own x is NOT in its own history: changing x[k] changes z[k] but week k's mean/sd come from weeks < k only
    xs3 = list(xs)
    xs3[25] += 1.0
    plans3, ld3 = synthetic_weeks(xs3)
    alt3 = cc.signal_weeks(plans3, ld3)
    a25 = np.array(xs[:25])
    approx(alt3[25]["z"], (xs3[25] - a25.mean()) / a25.std(ddof=1), 1e-9)


def test_thresholds_and_directions():
    hist = [0.0, 2.0] * 10  # mean 1, sample sd sqrt(20/19)
    sd = math.sqrt(20 / 19)
    for x, want in ((1 - sd, -1), (1 + sd, 1), (1 - 0.99 * sd, 0), (1 + 0.99 * sd, 0), (1.0, 0), (1 - 2 * sd, -1), (1 + 3 * sd, 1)):
        plans, ld = synthetic_weeks(hist + [x])
        r = cc.signal_weeks(plans, ld)[-1]
        assert r["direction"] == want, (x, r["z"], want)
    # low PCR (call-heavy, z <= -1) is SHORT; high PCR (put-heavy) is LONG
    plans, ld = synthetic_weeks(hist + [-5.0])
    r = cc.signal_weeks(plans, ld)[-1]
    assert r["z"] < -1 and r["direction"] == -1 and r["pcr"] < 1


def test_no_lookahead_signal_uses_only_candles_up_to_0925():
    base_tbl = {(25000, "CE"): leg(300.0), (25000, "PE"): leg(450.0), (25050, "CE"): leg(100.0), (25050, "PE"): leg(120.0)}
    r0 = cc.pcr_of_week(plan(), loader_from(base_tbl))
    # wild values in every candle AFTER 09:25 must not matter
    wild = {k: leg(v["oi"].iloc[2], extra_after=9e9) for k, v in base_tbl.items()}
    r1 = cc.pcr_of_week(plan(), loader_from(wild))
    assert r0["x"] == r1["x"] and r0["call_oi"] == r1["call_oi"] == 400.0 and r0["put_oi"] == 570.0
    # files that END at 09:25 give the same answer
    cut = {k: v.loc[v.index <= T925] for k, v in base_tbl.items()}
    assert cc.pcr_of_week(plan(), loader_from(cut))["x"] == r0["x"]
    # a 09:30 candle must not be used when the 09:25 one is absent (no forward-fill, no later-bar fallback)
    no925 = {k: v.drop(T925) for k, v in base_tbl.items()}
    assert cc.pcr_of_week(plan(), loader_from(no925))["skipped"] == "no_oi_at_signal"
    # a spy loader: the signal only ever asks for the 09:25 timestamp via oi_at (candles are read at one timestamp)
    seen = []
    orig = cc.oi_at
    cc.oi_at = lambda leg_, ts: (seen.append(ts), orig(leg_, ts))[1]
    try:
        cc.pcr_of_week(plan(), loader_from(base_tbl))
    finally:
        cc.oi_at = orig
    assert seen and set(seen) == {T925}


# ----------------------------------------------------------------------------------------------- skipped-week accounting
def test_skipped_week_accounting():
    xs = [0.0, 0.1] * 12  # weeks 0..23 valid
    plans, ld = synthetic_weeks(xs + [0.0, 0.0, 0.0, 0.0])
    plans[3]["skipped"] = "no_0925_bar"  # no signal bar
    ex_missing = plans[5]["expiry"]
    inner = ld
    ld2 = lambda ex, k, kind: None if ex == ex_missing else inner(ex, k, kind)  # noqa: E731  no files at all that week (like 2024-12-26)
    sig = cc.signal_weeks(plans, ld2)
    s = cc.skip_summary(sig)
    assert s["n_weeks"] == 28 and s["n_with_z"] + s["n_skipped"] == 28
    r = s["by_reason"]
    assert r["no_0925_bar"]["n"] == 1 and r["no_oi_at_signal"]["n"] == 1
    # weeks 0..21 minus the 2 data-less weeks (20 weeks with an x) have < 20 prior x values -> lt20_history; the data-less weeks do not feed the history
    assert r["lt20_history"]["n"] == 20
    # 20 valid x values exist before week 22 (22 weeks minus the 2 without data): first z appears at week 22
    first = next(x for x in sig if x["z"] is not None)
    assert first["k"] == 22
    for x in sig[:22]:
        assert x["z"] is None


# ----------------------------------------------------------------------------------------------- trades: payoff signs and cost
def bars_two_days():
    ts = [pd.Timestamp("2025-01-03 09:25"), pd.Timestamp("2025-01-03 09:30"), pd.Timestamp("2025-01-03 09:35"), pd.Timestamp("2025-01-03 09:40")]
    return pd.DataFrame({"open": [100.0, 100.0, 101.0, 102.0], "close": [99.0, 100.5, 101.5, 102.5]}, index=pd.DatetimeIndex(ts, name="date"))


def one_sig(direction, z=-1.5):
    return [{"k": 0, "expiry": date(2025, 1, 9), "entry_day": date(2025, 1, 3), "z": z, "pcr": 0.9, "direction": direction, "skipped": None}]


def test_payoff_signs_and_cost():
    b = bars_two_days()
    pl = [plan()]
    up = cc.build_trades(pl, one_sig(1), b, {date(2025, 1, 9): 110.0})
    t = up["trades"][0]  # long, entry open of 09:30 bar = 100, exit 110
    approx(t["gross"], 0.10)
    approx(t["net_ret"], 0.10 - 0.001)
    approx(t["net_rs"], 10 * 75 - 0.001 * 100 * 75)  # 750 - 7.5
    sh = cc.build_trades(pl, one_sig(-1), b, {date(2025, 1, 9): 90.0})["trades"][0]  # short, price falls 10%: profit
    approx(sh["net_ret"], 0.10 - 0.001)
    approx(sh["net_rs"], 750 - 7.5)
    lose = cc.build_trades(pl, one_sig(-1), b, {date(2025, 1, 9): 110.0})["trades"][0]  # short, price rises: loss, cost still charged
    approx(lose["net_ret"], -0.10 - 0.001)
    approx(lose["net_rs"], -750 - 7.5)
    flat = cc.build_trades(pl, one_sig(1), b, {date(2025, 1, 9): 100.0})["trades"][0]  # no move: pay the cost only
    approx(flat["net_ret"], -0.001)
    flip = cc.build_trades(pl, one_sig(1), b, {date(2025, 1, 9): 110.0}, flip=True)["trades"][0]  # opposite direction
    assert flip["direction"] == -1
    approx(flip["net_ret"], -0.10 - 0.001)
    # delayed entry uses the open of the 09:35 / 09:40 bar, same exit
    d1 = cc.build_trades(pl, one_sig(1), b, {date(2025, 1, 9): 110.0}, delay=1)["trades"][0]
    d2 = cc.build_trades(pl, one_sig(1), b, {date(2025, 1, 9): 110.0}, delay=2)["trades"][0]
    assert d1["entry"] == 101.0 and d2["entry"] == 102.0
    approx(d1["net_ret"], 110 / 101 - 1 - 0.001)
    lost = cc.build_trades(pl, one_sig(1), b, {date(2025, 1, 9): 110.0}, delay=3)
    assert lost["trades"] == [] and lost["lost"] == [("2025-01-09", "no_entry_bar_after_delay")]
    # no signal (direction 0) is an eligible week for the null pool but not a trade
    nt = cc.build_trades(pl, one_sig(0), b, {date(2025, 1, 9): 110.0})
    assert nt["trades"] == [] and len(nt["cand"]) == 1
    approx(nt["cand"][0], 0.10)
    # a week without z is neither
    nz = cc.build_trades(pl, [dict(one_sig(0)[0], z=None)], b, {date(2025, 1, 9): 110.0})
    assert nz["trades"] == [] and nz["cand"] == []


def test_evaluate_hand_numbers_and_zero_cost():
    b = bars_two_days()
    pls, sigs = [], []
    for i, (d, ex) in enumerate(((1, 110.0), (-1, 110.0), (1, 90.0))):
        pl = dict(plan(k=i, expiry=date(2025, 1, 9) + timedelta(days=7 * i)))
        pls.append(pl)
        sigs.append(dict(one_sig(d)[0], k=i, expiry=pl["expiry"]))
    closes = {pls[0]["expiry"]: 110.0, pls[1]["expiry"]: 110.0, pls[2]["expiry"]: 90.0}
    tr = cc.build_trades(pls, sigs, b, closes)
    ev = cc.evaluate(tr)
    # nets: +0.099, -0.101, -0.101 ; mean = -0.034333...
    approx(ev["mean_net"], (0.099 - 0.101 - 0.101) / 3)
    approx(ev["mean_zero_cost"], (0.10 - 0.10 - 0.10) / 3)
    assert ev["n_trades"] == 3 and ev["n_long"] == 2 and ev["n_short"] == 1
    approx(ev["worst_trade_ret"], -0.101)
    approx(ev["worst_trade_rs"], -750 - 7.5)
    # cumulative rupees 742.5, -15, -772.5: peak 742.5 -> trough -772.5 = drawdown -1515
    approx(ev["max_drawdown_rs"], -(757.5 + 757.5), 1e-9)
    assert ev["verdict"] == "REJECT"


# ----------------------------------------------------------------------------------------------- entry timing (wheel fix)
def test_entry_day_is_after_previous_expiry_and_muhurat_is_skipped():
    expiries = [date(2025, 1, 2), date(2025, 1, 9), date(2025, 1, 16)]  # Thursdays
    rows = []
    for d in (date(2024, 12, 26), date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 6), date(2025, 1, 9), date(2025, 1, 10), date(2025, 1, 13), date(2025, 1, 16)):
        for t in ("09:15", "09:20", "09:25", "09:30", "09:35"):
            rows.append({"date": pd.Timestamp(f"{d} {t}"), "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0 + d.day * 0.01, "volume": 0})
    bars = pd.DataFrame(rows)
    plans = cc.make_plans(bars, expiries)
    assert plans[1]["entry_day"] == date(2025, 1, 3)  # Friday after Thursday 2025-01-02 (NOT the expiry day itself)
    assert plans[2]["entry_day"] == date(2025, 1, 10)
    assert plans[1]["skipped"] is None and plans[1]["sig_ts"] == pd.Timestamp("2025-01-03 09:25")
    approx(plans[1]["spot"], 100.0 + 3 * 0.01)  # S = close of the 09:25 bar of the entry day
    # a Muhurat-style session has no 09:25 bar: the week is skipped, not moved
    muh = pd.DataFrame([{"date": pd.Timestamp("2025-01-10 18:00"), "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0}])
    b2 = pd.concat([bars[bars["date"].dt.date != date(2025, 1, 10)], muh], ignore_index=True)
    p2 = cc.make_plans(b2, expiries)
    assert p2[2]["entry_day"] == date(2025, 1, 10) and p2[2]["skipped"] == "no_0925_bar"
    # a day with a 09:25 bar but no 09:30 bar
    b3 = bars[~((bars["date"].dt.date == date(2025, 1, 10)) & (bars["date"].dt.strftime("%H%M") == "0930"))]
    assert cc.make_plans(b3, expiries)[2]["skipped"] == "no_0930_bar"


# ----------------------------------------------------------------------------------------------- statistics, halves, verdict
def test_halves_split_at_calendar_midpoint():
    mk = lambda d, n: {"k": 0, "expiry": d, "entry_day": d, "z": -2.0, "pcr": 1.0, "direction": 1, "entry": 100.0, "exit": 100.0 + n, "gross": n / 100,  # noqa: E731
                       "net_ret": n / 100 - 0.001, "gross_dir_ret": n / 100, "net_rs": n * 75.0}
    trs = {"trades": [mk(date(2025, 7, 9), 1), mk(date(2025, 7, 10), 2), mk(date(2025, 7, 11), -1)], "cand": [0.01, 0.02, -0.01, 0.0], "lost": []}
    h = cc.fi.halves(cc.to_fi_trades(trs), cc.COST)
    assert h["midpoint"] == "2025-07-10" and h["first_n"] == 2 and h["second_n"] == 1  # 2025-07-10 12:00 midpoint: the 10th is in the first half
    approx(h["first_mean"], (0.01 - 0.001 + 0.02 - 0.001) / 2)


def test_verdict_mapping():
    ok = {"n_trades": 25, "mean_net": 0.01, "boot_p": 0.001, "null_p": 0.001, "first_n": 12, "second_n": 13, "first_mean": 0.01, "second_mean": 0.02}
    assert cc.verdict(ok)[0] == "SURVIVES"
    assert cc.verdict(dict(ok, n_trades=19))[0] == "INCONCLUSIVE"  # fewer than 20 trades blocks the strict pass
    assert cc.verdict(dict(ok, second_mean=-0.01))[0] == "INCONCLUSIVE"
    assert cc.verdict(dict(ok, null_p=0.2))[0] == "INCONCLUSIVE"
    assert cc.verdict(dict(ok, boot_p=0.004))[0] == "INCONCLUSIVE"  # 0.004 > 0.003333 but < 0.05
    assert cc.verdict(dict(ok, boot_p=0.06))[0] == "REJECT"
    assert cc.verdict(dict(ok, mean_net=-0.001, boot_p=0.001))[0] == "REJECT"
    approx(cc.ALPHA, 0.05 / 15)
    assert cc.TOTAL_TRIALS == 15 and cc.TRIAL_ID == "B5-01"


def test_bootstrap_and_null_are_the_batch1_functions_with_blocks_of_3():
    x = np.array([0.02] * 10 + [-0.001] * 3)
    p3 = cc.fi.bootstrap_p(x, block=3, n_boot=2000)
    assert 0 < p3 <= 1
    assert cc.BLOCK == 3 and cc.N_BOOT == 10_000 and cc.N_NULL == 10_000 and cc.fi.SEED == 20261018
    # null: when the rule picks the best weeks of the pool, the null p is small
    pool = list(np.linspace(-0.02, 0.02, 40))
    best = sorted(pool)[-5:]
    trs = {"trades": [{"k": i, "expiry": date(2025, 1, 1) + timedelta(days=7 * i), "entry_day": date(2025, 1, 1) + timedelta(days=7 * i), "z": -2, "pcr": 1.0,
                       "direction": 1, "entry": 100.0, "exit": 100 * (1 + g), "gross": g, "net_ret": g - cc.COST, "gross_dir_ret": g, "net_rs": 0.0}
                      for i, g in enumerate(best)], "cand": pool, "lost": []}
    p, m, q = cc.fi.null_p(cc.to_fi_trades(trs), cc.COST, 2000)
    assert p < 0.01 and m < q


# ----------------------------------------------------------------------------------------------- hygiene
def code_strings(src: str) -> list:
    """Every string literal and identifier in the code, EXCLUDING docstrings (so a docstring that says 'never touches the ledger' is not a hit)."""
    import ast
    tree = ast.parse(src)
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr) \
                and isinstance(getattr(node.body[0], "value", None), ast.Constant) and isinstance(node.body[0].value.value, str):
            doc_nodes.add(id(node.body[0].value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_nodes:
            out.append(node.value)
        elif isinstance(node, ast.Name):
            out.append(node.id)
        elif isinstance(node, ast.Attribute):
            out.append(node.attr)
    return out


def test_no_holdout_no_order_code_no_ledger_write():
    banned = ("nifty_holdout", "ledger_loop", "place_order", "/v2/order", "/order/place", "KITE_", "access_token", "HOLDOUT_DIR", "_holdout")
    for f in sorted(HERE.glob("crowd_*.py")):
        for s in code_strings(f.read_text()):
            for b in banned:
                assert b not in s, (f.name, b, s)
    assert "UPSTOX_ANALYTICS_TOKEN" not in "".join(code_strings((HERE / "crowd_download.py").read_text()))  # the token name never appears in my code: upstox_api reads it


if __name__ == "__main__":
    fails = 0
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for n, f in tests:
        try:
            f()
            print("ok  ", n)
        except Exception as e:  # noqa: BLE001
            fails += 1
            print("FAIL", n, type(e).__name__, e)
    print(f"{len(tests) - fails} tests passed" if not fails else f"{fails} FAILED")
    sys.exit(1 if fails else 0)
