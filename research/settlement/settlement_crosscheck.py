"""Independent plain-CSV re-computation of Task 7 (G0, T1, T2, T3): csv module + hand arithmetic only. It shares NO code with
settlement_core.py / settlement_run.py (fees re-derived by hand, strikes rounded with its own rule, own random draws with a different seed).
Prints the largest per-day difference against results/t1_days.csv, t2_days.csv, t3_days.csv and the headline numbers."""

import csv
import math
import random
import statistics
from datetime import datetime
from pathlib import Path

R = Path(__file__).resolve().parent.parent
D, OUT = R / "data", Path(__file__).resolve().parent / "results"
Q = 75


def side(prem, buy):
    t = prem * Q
    ex, se = 0.0003553 * t, 0.000001 * t
    return 20 + ex + se + 0.18 * (20 + ex + se) + (0.00003 * t if buy else 0.0015 * t)


bars = {}
for r in csv.DictReader(open(D / "nifty_5minute_dev.csv")):
    ts = datetime.fromisoformat(r["date"])
    bars[ts] = (float(r["open"]), float(r["close"]))
daily = {r["date"][:10]: float(r["close"]) for r in csv.DictReader(open(D / "nifty_day_dev.csv"))}
exps = [r["expiry"] for r in csv.DictReader(open(D / "nifty_expiries.csv"))]
exps = [e for e in exps if "2024-10-03" <= e <= "2026-04-16"]


def candles(e, k, kind):
    p = D / "expired_options" / "NIFTY" / f"{e}_{k}{kind}.csv"
    if not p.exists():
        return None
    return {datetime.fromisoformat(r["date"]): (float(r["open"]), float(r["oi"]) if r["oi"] not in ("", "nan") else None) for r in csv.DictReader(open(p))}


def nearest50(x):
    q, rem = divmod(x, 50)
    return int(q * 50 + (50 if rem >= 25 else 0))  # halves up


# ---- G0
a_s0, s1_s0 = [], []
for e in exps:
    t0, t1 = datetime.fromisoformat(e + "T15:00:00"), datetime.fromisoformat(e + "T15:25:00")
    if t0 in bars and t1 in bars and e in daily:
        a_s0.append(daily[e] - bars[t0][0])
        s1_s0.append(bars[t1][1] - bars[t0][0])
print(f"G0 n={len(a_s0)} ratio={statistics.stdev(a_s0) / statistics.stdev(s1_s0):.6f}")

# ---- T1 / T2
for name, wings in (("t1", False), ("t2", True)):
    ref = {r["expiry"]: r for r in csv.DictReader(open(OUT / f"{name}_days.csv"))}
    worst, mine, skipped = 0.0, {}, 0
    nets = {0.10: [], 0.20: [], 0.30: []}
    for e in exps:
        t0 = datetime.fromisoformat(e + "T15:00:00")
        if t0 not in bars or e not in daily:
            skipped += 1
            continue
        k = nearest50(bars[t0][0])
        legs = [("CE", k, False), ("PE", k, False)] + ([("CE", k + 100, True), ("PE", k - 100, True)] if wings else [])
        op = []
        for kind, kk, buy in legs:
            c = candles(e, kk, kind)
            px = c[t0][0] if c and t0 in c else 0.0
            op.append(px)
        if min(op) <= 0:
            skipped += 1
            continue
        a = daily[e]
        for sl in nets:
            net = 0.0
            for (kind, kk, buy), px in zip(legs, op):
                fill = max(px + sl, 0) if buy else max(px - sl, 0)
                intr = max(a - kk, 0) if kind == "CE" else max(kk - a, 0)
                sign = -1 if buy else 1
                net += sign * (fill - intr) * Q - side(fill, buy) - 0.0015 * intr * Q
            nets[sl].append(net)
            if sl == 0.20:
                mine[e] = net
        if e in ref:
            worst = max(worst, abs(mine[e] - float(ref[e]["net_0.20"])))
    only_ref = set(ref) - set(mine)
    only_me = set(mine) - set(ref)
    print(f"{name.upper()} n={len(mine)} skipped={skipped} | mean net 0.10/0.20/0.30 = " + " / ".join(f"{statistics.fmean(nets[s]):+.2f}" for s in nets)
          + f" | max |diff| per day vs harness = {worst:.9f} | days only in harness {len(only_ref)}, only here {len(only_me)}")
    cum, peak, dd = 0.0, 0.0, 0.0
    for e in sorted(mine):
        cum += mine[e]
        peak = max(peak, cum)
        dd = min(dd, cum - peak)
    print(f"   worst trade {min(mine.values()):+.2f}, max drawdown {dd:+.2f}")

# ---- T3
ref = {r["expiry"]: r for r in csv.DictReader(open(OUT / "t3_days.csv"))}
dm, rand_exp, dists_all = {}, {}, {}
for e in exps:
    t0 = datetime.fromisoformat(e + "T15:00:00")
    if t0 not in bars or e not in daily:
        continue
    k0 = nearest50(bars[t0][0])
    cut = datetime.fromisoformat(e + "T14:50:00")
    pair = {}
    for k in range(k0 - 500, k0 + 501, 50):
        tot = []
        for kind in ("CE", "PE"):
            c = candles(e, k, kind)
            oi = [c[t][1] for t in sorted(c) if t <= cut and t.date() == cut.date() and c[t][1] is not None] if c else []
            tot.append(oi[-1] if oi else None)
        if None not in tot:
            pair[k] = sum(tot)
    if len(pair) < 3:
        continue
    top = max(pair.values())
    kmax = min(k for k in pair if pair[k] == top)
    a = daily[e]
    dm[e] = abs(a - kmax)
    dists_all[e] = [abs(a - k) for k in sorted(pair)]
    rand_exp[e] = statistics.fmean(dists_all[e])
diff = max([abs(dm[e] - float(ref[e]["dist_max"])) for e in dm if e in ref] + [0])
print(f"T3 n={len(dm)} (harness {len(ref)}) max |diff| of dist_max vs harness = {diff:.9f}; observed mean {statistics.fmean(dm.values()):.4f}; expected random {statistics.fmean(rand_exp.values()):.4f}")
random.seed(7)
obs = statistics.fmean(dm.values())
draws = 10_000
le = 0
for _ in range(draws):
    m = statistics.fmean(random.choice(dists_all[e]) for e in dists_all)
    le += m <= obs
print(f"   own Monte Carlo (seed 7) one-sided p = {(1 + le) / (draws + 1):.4f}")
