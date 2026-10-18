"""Independent recomputation of the headline means (plain csv + loops, no pandas/numpy) for ideas 1-4, 6-9.
  python research/ideas/crosscheck_ideas.py   -> compares with results/ideas_batch1_results.json"""
import csv, json
from datetime import date, datetime, timedelta
from pathlib import Path

H = Path(__file__).resolve().parent
D = H.parent / "data"
rows = [(date.fromisoformat(r["date"][:10]), float(r["open"]), float(r["close"])) for r in csv.DictReader(open(D / "nifty_day_dev.csv"))]
C = 0.001
def mean(x): return sum(x) / len(x) if x else float("nan")
out = {}
# 1
by = {}
for i, (d, o, c) in enumerate(rows): by.setdefault((d.year, d.month), []).append(i)
keys = sorted(by); r1 = []
for k in keys[:-1]:
    nk = (k[0] + (k[1] // 12), k[1] % 12 + 1)
    if nk in by and len(by[k]) >= 2 and len(by[nk]) >= 3:
        r1.append(rows[by[nk][2]][2] / rows[by[k][-2]][2] - 1 - C)
out[1] = (len(r1), mean(r1))
out[2] = (len(rows) - 1, mean([rows[i + 1][1] / rows[i][2] - 1 - C for i in range(len(rows) - 1)]))
r3, r4, r8, r9 = [], [], [], []
for i in range(1, len(rows)):
    gap = rows[i][1] / rows[i - 1][2] - 1
    if abs(gap) > 0.007 + 1e-12: r3.append((-1 if gap > 0 else 1) * (rows[i][2] / rows[i][1] - 1) - C)
    if rows[i][2] / rows[i - 1][2] - 1 <= -0.02 + 1e-12 and i + 1 < len(rows): r4.append(rows[i + 1][2] / rows[i + 1][1] - 1 - C)
out[3], out[4] = (len(r3), mean(r3)), (len(r4), mean(r4))
for i in range(len(rows) - 1):
    a, b = rows[i][0], rows[i + 1][0]; x = a + timedelta(1)
    miss = 0
    while x < b:
        miss += x.weekday() < 5; x += timedelta(1)
    if miss >= 1: r8.append(rows[i + 1][1] / rows[i][2] - 1 - C)
out[8] = (len(r8), mean(r8))
pos = {d: i for i, (d, o, c) in enumerate(rows)}
for i, (d, o, c) in enumerate(rows):
    if d.weekday() == 4 and d + timedelta(3) in pos: r9.append(rows[pos[d + timedelta(3)]][2] / c - 1 - C)
out[9] = (len(r9), mean(r9))
bars = {}
for r in csv.DictReader(open(D / "nifty_5minute_dev.csv")):
    t = datetime.fromisoformat(r["date"]); bars[(t.date(), t.strftime("%H%M"))] = (float(r["open"]), float(r["close"]))
days = sorted({k[0] for k in bars}); r6, r7 = [], []
for d in days:
    try:
        s = bars[(d, "1515")][0] / bars[(d, "1415")][0] - 1; g = bars[(d, "1525")][1] / bars[(d, "1515")][0] - 1
        if s: r6.append((1 if s > 0 else -1) * g - C)
    except KeyError: pass
    try:
        s = bars[(d, "0940")][1] / bars[(d, "0915")][0] - 1; g = bars[(d, "1515")][0] / bars[(d, "0945")][0] - 1
        if s: r7.append((1 if s > 0 else -1) * g - C)
    except KeyError: pass
out[6], out[7] = (len(r6), mean(r6)), (len(r7), mean(r7))
res = {r["idea"]: r for r in json.load(open(H / "results" / "ideas_batch1_results.json"))["results"]}
worst = 0
for k, (n, m) in sorted(out.items()):
    diff = abs(m - res[k]["mean_net"]); worst = max(worst, diff)
    print(f"idea {k}: n {n} vs {res[k]['n_trades']}  mean {m:+.6f} vs {res[k]['mean_net']:+.6f}")
    assert n == res[k]["n_trades"], k
print("max |mean difference| =", worst); assert worst < 1e-12
