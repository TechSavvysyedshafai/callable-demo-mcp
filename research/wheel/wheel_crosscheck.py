"""Independent plain-CSV re-computation of Task 8 (wheel, put-only and call-only controls, benchmark) at slippage Rs0.20: csv module + hand arithmetic only.
It shares NO code with wheel_core.py / wheel_run.py (entry days, strikes, fees, state machine and benchmark are all re-derived here with plain loops).
Prints the largest per-week difference against results/weeks_<mode>_0.20.csv and the headline totals."""

import csv
import math
from datetime import date, datetime, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent.parent
D, OUT = R / "data", Path(__file__).resolve().parent / "results"
SLIP, Q = 0.20, 75


def sell_fee(prem):
    t = prem * Q
    ex, se = 0.0003553 * t, 0.000001 * t
    return 20 + ex + se + 0.18 * (20 + ex + se) + 0.0015 * t


bars = [(datetime.fromisoformat(r["date"]), float(r["close"])) for r in csv.DictReader(open(D / "nifty_5minute_dev.csv"))]
daily = {r["date"][:10]: float(r["close"]) for r in csv.DictReader(open(D / "nifty_day_dev.csv"))}
days = sorted({b[0].date() for b in bars})
exps = [date.fromisoformat(r["expiry"]) for r in csv.DictReader(open(D / "nifty_expiries.csv"))]
exps = [e for e in exps if date(2024, 10, 3) <= e <= date(2026, 4, 16)]
exps.sort()


def opens(e, strike, kind):
    p = D / "expired_options" / "NIFTY" / f"{e}_{strike}{kind}.csv"
    if not p.exists():
        return None
    return {datetime.fromisoformat(r["date"]): float(r["open"]) for r in csv.DictReader(open(p))}


# entry plans: later of (nearest trading day on or before expiry-7) and (first trading day after the previous expiry)
plans = []
for k, e in enumerate(exps):
    a = max(d for d in days if d <= e - timedelta(days=7))
    day = a if k == 0 else max(a, min(d for d in days if d > exps[k - 1]))
    i = next(j for j, b in enumerate(bars) if b[0].date() == day and b[0].hour * 60 + b[0].minute >= 570)
    ts, spot = bars[i]
    plans.append((e, day, ts, spot, math.floor(round(spot * 0.988 / 50, 9)) * 50, math.ceil(round(spot * 1.012 / 50, 9)) * 50))

first_spot = plans[0][3]
n = len(plans)


def run(mode):
    out = {}
    state = "LONG" if mode == "call_only" else "CASH"
    prev = first_spot
    for i, (e, day, ts, spot, put, call) in enumerate(plans):
        s = daily[e.isoformat()]
        net = 0.0
        if state == "LONG":
            net += (s - prev) * Q
            if mode == "call_only" and i == 0:
                net -= 0.00065 * first_spot * Q
        kind = "CE" if state == "LONG" else "PE"
        k = call if kind == "CE" else put
        c = opens(e, k, kind)
        traded = c is not None and ts in c and c[ts] - SLIP > 0
        if traded:
            f = max(c[ts] - SLIP, 0)
            iv = max(s - k, 0) if kind == "CE" else max(k - s, 0)
            net += f * Q - sell_fee(f) - iv * Q - 0.0015 * iv * Q
            if mode == "wheel" and kind == "PE" and s < k:
                state = "LONG"
                net -= 0.00065 * k * Q
            elif mode == "wheel" and kind == "CE" and s > k:
                state = "CASH"
                net -= 0.00065 * k * Q
        if i == n - 1 and state == "LONG":
            net -= 0.00065 * s * Q
        out[e.isoformat()] = (net, traded)
        prev = s
    return out


bench, prev = {}, first_spot
for i, (e, *_r) in enumerate(plans):
    s = daily[e.isoformat()]
    v = (s - prev) * Q - (0.00065 * first_spot * Q if i == 0 else 0) - (0.00065 * s * Q if i == n - 1 else 0)
    bench[e.isoformat()] = v
    prev = s

worst = 0.0
for mode in ("wheel", "put_only", "call_only"):
    mine = run(mode)
    theirs = {r["expiry"]: (float(r["net_rs"]), float(r["bench_rs"])) for r in csv.DictReader(open(OUT / f"weeks_{mode}_0.20.csv"))}
    dn = max(abs(mine[k][0] - theirs[k][0]) for k in mine)
    db = max(abs(bench[k] - theirs[k][1]) for k in mine)
    worst = max(worst, dn, db)
    tot, btot = sum(v[0] for v in mine.values()), sum(bench.values())
    mean_d = (tot - btot) / n
    print(f"{mode}: weeks {len(mine)} (traded {sum(v[1] for v in mine.values())}) total net Rs {tot:,.2f}; benchmark total Rs {btot:,.2f}; mean D Rs {mean_d:,.2f}; "
          f"same weeks: {mine.keys() == theirs.keys()}; max abs weekly difference net Rs {dn:.9f}, benchmark Rs {db:.9f}")
print("largest difference anywhere: Rs", worst)
