"""Independent recomputation of the B7-01 headline from the raw files, STANDARD LIBRARY ONLY (csv, math, statistics, random, glob). Shares no code with
crypto_core.py / crypto_run.py. It reads the PARSED daily metrics CSVs and the monthly daily-kline CSVs, rebuilds x, z, the signals, the trades and the
net returns by plain loops, then compares them with the engine's trades_{SYM}.csv one by one. The bootstrap p is re-derived with a separate loop (Python's
random module, not numpy: it will not reproduce the engine's p digit for digit, so it is compared within sampling error).
  python research/crypto/crypto_crosscheck.py     (run after crypto_run.py)"""

import csv
import glob
import math
import os
import random
import statistics
import sys
from datetime import date, datetime, timedelta

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.join(ROOT, "data", "crypto")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
LAST = date(2025, 12, 31)
COST = 0.0012


def read_x(sym):
    """{date: ln(ratio at 23:50:00)} - the first row with that stamp wins."""
    xs = {}
    for path in sorted(glob.glob(os.path.join(DATA, "parsed", "metrics", sym, "*.csv"))):
        d = date.fromisoformat(os.path.basename(path)[-14:-4])
        assert d <= LAST
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                if row["create_time"] == f"{d.isoformat()} 23:50:00":
                    try:
                        v = float(row["count_long_short_ratio"])
                    except ValueError:
                        break
                    if v > 0:
                        xs[d] = math.log(v)
                    break
    return xs


def read_opens(sym):
    px = {}
    for path in sorted(glob.glob(os.path.join(DATA, "parsed", "klines1d", sym, "*.csv"))):
        with open(path, newline="") as f:
            for row in csv.reader(f):
                if not row[0].isdigit():
                    continue
                t = int(row[0])
                t = t / 1e6 if t > 1e14 else t / 1e3
                d = (datetime(1970, 1, 1) + timedelta(seconds=t)).date()
                assert d <= LAST
                px.setdefault(d, float(row[1]))
    return px


def trades_for(sym):
    xs, px = read_x(sym), read_opens(sym)
    days = sorted(xs)
    out, pool = [], 0
    hist = []
    for d in days:
        prior = hist[-90:]
        if len(prior) >= 60:
            m = sum(prior) / len(prior)
            var = sum((a - m) ** 2 for a in prior) / (len(prior) - 1)
            sd = math.sqrt(var)
            if sd > 0:
                z = (xs[d] - m) / sd
                e, x = px.get(d + timedelta(days=1)), px.get(d + timedelta(days=2))
                if e is not None and x is not None and d + timedelta(days=2) <= LAST:
                    pool += 1
                    direction = -1 if z >= 1.5 - 1e-12 else (1 if z <= -1.5 + 1e-12 else 0)
                    if direction:
                        out.append((d, direction, z, direction * (x / e - 1) - COST))
        hist.append(xs[d])
    return out, pool


def boot_p(net, block=5, n=10000, seed=7):
    rng = random.Random(seed)
    m = len(net)
    mu = sum(net) / m
    k = -(-m // block)
    hits = 0
    for _ in range(n):
        s = []
        for _ in range(k):
            st = rng.randrange(0, m - block + 1)
            s.extend(net[st:st + block])
        s = s[:m]
        if sum(s) / m - mu >= mu:
            hits += 1
    return (1 + hits) / (n + 1)


def main():
    ok = True
    for sym in ("BTCUSDT", "ETHUSDT"):
        tr, pool = trades_for(sym)
        eng = {}
        with open(os.path.join(OUT, f"trades_{sym}.csv"), newline="") as f:
            for r in csv.DictReader(f):
                eng[r["signal_date"][:10]] = (int(r["direction"]), float(r["z"]), float(r["net"]))
        mine = {d.isoformat(): (dr, z, net) for d, dr, z, net in tr}
        same_set = set(mine) == set(eng)
        dmax_z = max((abs(mine[k][1] - eng[k][1]) for k in mine if k in eng), default=float("nan"))
        dmax_net = max((abs(mine[k][2] - eng[k][2]) for k in mine if k in eng), default=float("nan"))
        same_dir = all(mine[k][0] == eng[k][0] for k in mine if k in eng)
        net = [t[3] for t in tr]
        mean = sum(net) / len(net)
        p = boot_p(net)
        print(f"{sym}: independent trades {len(tr)} vs engine {len(eng)}; same trade dates {same_set}; same directions {same_dir}; "
              f"max |z diff| {dmax_z:.2e}; max |net diff| {dmax_net:.2e}; eligible pool days {pool}")
        print(f"   mean net {mean * 100:+.4f}%   (long {sum(1 for t in tr if t[1] > 0)}, short {sum(1 for t in tr if t[1] < 0)})   worst {min(net) * 100:+.3f}%   independent bootstrap p {p:.4f}")
        ok &= same_set and same_dir and dmax_z < 1e-9 and dmax_net < 1e-12
    print("CROSSCHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
