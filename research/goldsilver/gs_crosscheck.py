"""Independent re-computation of B6-01 from the two plain CSV files: standard library only (csv, math, random), no numpy / pandas,
and NO import of gs_core. Different structure on purpose: a day-by-day state machine (open of day t: execute what was decided at the
close of day t-1; close of day t: decide) instead of the engine's trade-by-trade loop.
It re-reads the dev CSVs, rebuilds the common calendar, Z-scores, trades, costs and the summary numbers, then compares them with
research/goldsilver/results/goldsilver_results.json trade by trade.   python research/goldsilver/gs_crosscheck.py"""

import csv
import datetime as dt
import json
import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
CUT = "2026-04-16"


def read(name):
    rows = {}
    with open(DATA / name) as f:
        for r in csv.DictReader(f):
            d = r["date"][:10]
            if d <= CUT:
                rows[d] = (float(r["open"]), float(r["close"]))
    return rows


def run(lb=60, thr=2.0, exit_z=0.5, stop_z=4.0, max_hold=20):
    G, S = read("goldbees_day_dev.csv"), read("silverbees_day_dev.csv")
    days = sorted(d for d in G if d in S and min(G[d] + S[d]) > 0)
    go = [G[d][0] for d in days]
    so = [S[d][0] for d in days]
    r = [math.log(G[d][1] / S[d][1]) for d in days]
    n = len(days)

    def z_at(t):
        if t < lb - 1:
            return None
        w = r[t - lb + 1: t + 1]
        m = sum(w) / lb
        var = sum((x - m) ** 2 for x in w) / (lb - 1)
        return None if var <= 0 else (r[t] - m) / math.sqrt(var)

    out, pos, pend_entry, pend_exit, unfinished, skipped_sig = [], None, None, None, 0, 0
    for t in range(n):
        # ---- open of day t
        if pend_entry is not None and pend_entry[0] == t:
            pos = {"sig": pend_entry[1], "dir": pend_entry[2], "e": t}
            pend_entry = None
        if pend_exit == t and pos is not None:
            x = t
            e = pos["e"]
            gross = pos["dir"] * ((go[x] / go[e] - 1.0) - (so[x] / so[e] - 1.0))
            cal = (dt.date.fromisoformat(days[x]) - dt.date.fromisoformat(days[e])).days
            out.append({"entry": days[e], "exit": days[x], "dir": pos["dir"], "hold": x - e, "cal": cal, "gross": gross,
                        "net": gross - 0.002 - 0.0002 * cal})
            pos, pend_exit = None, None
        # ---- close of day t
        z = z_at(t)
        if pos is not None:
            if pend_exit is None and z is not None:
                k = t - pos["e"]
                if abs(z) <= exit_z + 1e-12 or abs(z) >= stop_z - 1e-12 or k == max_hold - 1:
                    pend_exit = t + 1
        elif pend_entry is None and z is not None:
            if z >= thr - 1e-12 or z <= -thr + 1e-12:
                if t + 1 >= n:
                    skipped_sig += 1
                else:
                    pend_entry = (t + 1, t, -1 if z > 0 else +1)
    if pos is not None or pend_entry is not None:
        unfinished += 1 if pos is not None else 0
    return days, out, unfinished, skipped_sig


def maxdd(x):
    c = peak = dd = 0.0
    for v in x:
        c += v
        peak = max(peak, c)
        dd = min(dd, c - peak)
    return dd


def boot_p(x, block=3, B=10000, seed=1):
    rnd = random.Random(seed)
    m, mean = len(x), sum(x) / len(x)
    k = -(-m // block)
    hits = 0
    for _ in range(B):
        s = []
        for _ in range(k):
            a = rnd.randrange(0, m - block + 1)
            s.extend(x[a:a + block])
        s = s[:m]
        if sum(s) / m - mean >= mean:
            hits += 1
    return (1 + hits) / (B + 1)


def main():
    days, tr, unfinished, skipped_sig = run()
    res = json.load(open(HERE / "results" / "goldsilver_results.json"))
    ref = res["trades"]
    print(f"common days {len(days)}  first {days[0]}  last {days[-1]}  silver listed (first row) {days[0]}")
    print(f"crosscheck trades {len(tr)} vs engine {len(ref)}; unfinished {unfinished} (engine {res['primary']['unfinished']}); skipped signals {skipped_sig} (engine {res['primary']['skipped_signals']})")
    ok = len(tr) == len(ref) and unfinished == res["primary"]["unfinished"]
    worst = 0.0
    for a, b in zip(tr, ref):
        same = (a["entry"], a["exit"], a["dir"], a["hold"], a["cal"]) == (b["entry_date"], b["exit_date"], b["direction"], b["hold"], b["cal_days"])
        diff = abs(a["gross"] - b["gross"])
        worst = max(worst, diff)
        if not same or diff > 1e-12:
            ok = False
            print("MISMATCH", a, b)
    net = [t["net"] for t in tr]
    gross = [t["gross"] for t in tr]
    mean = sum(net) / len(net)
    p = res["primary"]
    print(f"max |gross diff| over trades {worst:.3e}")
    for name, mine, theirs in (("mean net", mean, p["mean_net"]), ("mean gross (zero cost)", sum(gross) / len(gross), p["mean_gross"]),
                               ("worst trade", min(net), p["worst_net"]), ("max drawdown", maxdd(net), p["max_drawdown"]), ("total net", sum(net), p["total_net"])):
        d = abs(mine - theirs)
        print(f"  {name:<24} crosscheck {mine:+.8f}  engine {theirs:+.8f}  diff {d:.2e}")
        ok &= d < 1e-12
    mid = dt.date.fromisoformat(days[0]) + (dt.date.fromisoformat(days[-1]) - dt.date.fromisoformat(days[0])) / 2
    f = [t["net"] for t in tr if dt.date.fromisoformat(t["entry"]) <= mid]
    s = [t["net"] for t in tr if dt.date.fromisoformat(t["entry"]) > mid]
    print(f"  halves (mid {mid}) first n={len(f)} mean {sum(f)/len(f):+.6f} | second n={len(s)} mean {sum(s)/len(s):+.6f}   engine {p['first_mean']:+.6f} | {p['second_mean']:+.6f}")
    ok &= abs(sum(f) / len(f) - p["first_mean"]) < 1e-12 and abs(sum(s) / len(s) - p["second_mean"]) < 1e-12 and (len(f), len(s)) == (p["first_n"], p["second_n"])
    print(f"  bootstrap p (own RNG, approximate, different random numbers): {boot_p(net):.3f}   engine {p['boot_p']:.3f}")
    # the nine grid cells: trade counts and means
    for lb in (40, 60, 90):
        for th in (1.5, 2.0, 2.5):
            _, t2, _, _ = run(lb, th)
            m2 = sum(x["net"] for x in t2) / len(t2)
            g = res["grid"][f"{lb}_{th:.1f}"]
            good = len(t2) == g["n_trades"] and abs(m2 - g["mean_net"]) < 1e-12
            ok &= good
            print(f"  grid {lb}/{th}: n {len(t2)} mean {m2:+.6f}  engine n {g['n_trades']} mean {g['mean_net']:+.6f}  {'ok' if good else 'MISMATCH'}")
    print("CROSSCHECK", "AGREES with the engine" if ok else "DISAGREES")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
