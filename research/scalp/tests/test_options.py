"""Option-scalp self-checks: Black-Scholes sanity, expiry rules, costs, and the backtest on fake data."""

import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent.parent
for p in (HERE / "options", HERE, HERE.parent):
    sys.path.insert(0, str(p))
import bs
from contracts import UNDERLYINGS, next_expiry
from costs_opt import OptionCostModel
import evaluate_opt as eo
from synth import synthetic_intraday

# put-call parity and ATM delta
S, K, T, iv, r = 24000, 24000, 7 / 365, 0.14, 0.065
c, p = bs.price(S, K, T, iv, True), bs.price(S, K, T, iv, False)
assert abs((c - p) - (S - K * 2.718281828 ** (-r * T))) < 1e-6
assert 0.45 < bs.delta(S, K, T, iv, True) < 0.6
# expiry rules (weekly NIFTY on Tuesday; monthly index = last Tuesday)
assert next_expiry(UNDERLYINGS["NIFTY"], date(2026, 10, 12)).weekday() == 1
m = next_expiry(UNDERLYINGS["BANKNIFTY"], date(2026, 10, 12))
assert m.weekday() == 1 and m.month == 10 and (m.day + 7) > 31
# costs: round trip on a Rs150 premium costs ~1-2 premium points
be = OptionCostModel().breakeven_pts(150.0, 75)
assert 0.8 < be < 3.0, be
# backtest: no edge must not PASS; strong planted edge must PASS (IV 16 so option buyers pay a premium)
cfg = UNDERLYINGS["NIFTY"]
for phi, want in ((0.0, "FAIL"), (0.5, "PASS")):
    df = synthetic_intraday(n_days=200, phi=phi, bar_vol=0.0008)
    vix = {d: 16.0 for d in df["date"].dt.date.unique()}
    res = eo.evaluate(df, vix, cfg, trials=1, runs=40)
    assert res["verdict"] == want, (phi, res["verdict"], res.get("p_vs_random_entries"))
print("options ok")
