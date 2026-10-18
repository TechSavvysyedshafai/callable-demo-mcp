"""Independent re-computation of B0 and S1 (0.25% cost) with plain Python loops, sharing no code with backtest.py.
Run from research/:  python lowturn/crosscheck.py     (reads the DEV file only)"""

import csv
from datetime import date

rows = list(csv.DictReader(open("data/nifty_day_long_dev.csv")))
d = [date.fromisoformat(r["date"][:10]) for r in rows]
o = [float(r["open"]) for r in rows]
c = [float(r["close"]) for r in rows]
COST, RF = 0.0025, 1.065 ** (1 / 252) - 1


def run(weights, start):
    """weights[t] decided at close t; trade at open t+1. Day-by-day wealth, written the long way round."""
    wealth, peak, mdd, held = 1.0, 1.0, 0.0, 0.0
    first = d[start + 1]
    for t in range(start + 1, len(c)):
        new = weights[t - 1]
        before = wealth
        # overnight with the old weight, then trade at the open, then intraday with the new weight
        wealth = before * (1 + held * (o[t] / c[t - 1] - 1))
        wealth *= 1 - COST * abs(new - held)
        wealth *= 1 + new * (c[t] / o[t] - 1) + (1 - new) * RF
        held = new
        peak = max(peak, wealth)
        mdd = min(mdd, wealth / peak - 1)
    yrs = (d[-1] - first).days / 365.25
    return wealth ** (1 / yrs) - 1, mdd


s1 = [None] * len(c)
for t in range(199, len(c)):
    s1[t] = 1.0 if c[t] > sum(c[t - 199 : t + 1]) / 200 else 0.0
start = 0
# the shared evaluation window starts at the latest first-defined signal (S2 needs 10 month-ends) -> take it from the main run's JSON
import json
first = json.load(open("lowturn/results/lowturn_results.json"))["data"]["eval_first_decision"]
start = [str(x) for x in d].index(first)
print("window starts (first decision close):", first)
for name, w in (("B0", [1.0] * len(c)), ("S1", s1)):
    cagr, mdd = run(w, start)
    print(f"{name}: CAGR {cagr:.4%}  maxDD {mdd:.4%}")
