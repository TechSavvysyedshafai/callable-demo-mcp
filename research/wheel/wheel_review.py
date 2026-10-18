"""Hostile-review diagnostics for Task 8 (information only: NOT trials, NOT pass criteria, post-hoc and exploratory).
Reads research/wheel/results/weeks_*_0.20.csv written by wheel_run.py; prints beta/exposure, start-point effect, regime split, skipped weeks, lot-size eras."""

import csv
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wheel_core as wc  # noqa: E402

OUT = HERE / "results"


def load(mode):
    return list(csv.DictReader(open(OUT / f"weeks_{mode}_0.20.csv")))


def main():
    w = load("wheel")
    net = np.array([float(r["net_rs"]) for r in w])
    ben = np.array([float(r["bench_rs"]) for r in w])
    d = net - ben
    n = len(d)
    L = []
    beta, alpha = np.polyfit(ben, net, 1)
    resid = net - beta * ben
    L.append(f"1 BETA: slope of wheel weekly P&L on benchmark weekly P&L = {beta:.3f} (correlation {np.corrcoef(ben, net)[0, 1]:.3f}); weeks starting LONG {sum(r['state_start'] == 'LONG' for r in w)}/{n}. "
             f"Beta-adjusted weekly gain (wheel - beta x bench): mean Rs{resid.mean():+,.0f}, bootstrap p {wc.fi.bootstrap_p(resid):.4f} (exploratory, post-hoc, no pass rule).")
    L.append(f"   Meaning: the wheel carries about {beta:.0%} of the index's up/down moves, so in a falling window it 'beats' buy-and-hold partly by owning less of it. Sample index move: first entry spot -> last close = "
             f"{float(w[-1]['settle']) - float(w[0]['spot']):+,.0f} points ({(float(w[-1]['settle']) / float(w[0]['spot']) - 1):+.1%}).")
    L.append(f"2 START POINT: the benchmark is bought at the first entry bar, {w[0]['spot'][:8]} on {w[0]['entry_day']}, near the index's all-time high; week-0 D is Rs{d[0]:+,.0f}. Mean D over the other 80 weeks: Rs{d[1:].mean():+,.0f} "
             f"(bootstrap p {wc.fi.bootstrap_p(d[1:]):.4f}, post-hoc).")
    up, dn = ben > 0, ben < 0
    L.append(f"3 REGIME: weeks with benchmark up ({up.sum()}): mean D Rs{d[up].mean():+,.0f}; benchmark down ({dn.sum()}): mean D Rs{d[dn].mean():+,.0f}; weeks with D>0: {(d > 0).sum()}/{n}. "
             f"The 10 largest-|D| weeks sum to Rs{d[np.argsort(-np.abs(d))[:10]].sum():+,.0f} of total Rs{d.sum():+,.0f}.")
    big = np.argsort(d)[:5]
    L.append("   five worst D weeks: " + "; ".join(f"{w[i]['expiry']} Rs{d[i]:+,.0f} ({w[i]['state_start']}, {w[i]['event'] or 'no event'})" for i in big)
             + "  -> the wheel gives up the big rebounds: capped by calls, or sitting in CASH after the assignment.")
    trad = [r for r in w if not r["skipped"]]
    L.append(f"4 SKIPPED: {sum(1 for r in w if r['skipped'])} of {n}: " + "; ".join(f"{r['expiry']} ({r['state_start']}, {r['skipped']})" for r in w if r["skipped"])
             + f". Mean D with them excluded: Rs{np.mean([float(r['d_rs']) for r in trad]):+,.0f}.")
    odd = [r for r in w if r["entry_ts"][11:16] != "09:30"]
    L.append(f"4b ENTRY TIMES: {len(odd)} entries are not at 09:30 because the 'first trading day after the previous expiry' was a special Diwali Muhurat session: "
             + "; ".join(f"{r['expiry']} entered {r['entry_ts']} ({r['skipped'] or 'traded'})" for r in odd) + ". Rule left as pre-registered (changing it after seeing results would be a variant).")
    ev = Counter(r["event"] for r in w)
    L.append(f"5 PATH: assignments {ev['assigned']}, called away {ev['called_away']}; weeks CASH {sum(r['state_start'] == 'CASH' for r in w)}, LONG {sum(r['state_start'] == 'LONG' for r in w)}; "
             f"longest LONG streak {max_run([r['state_start'] == 'LONG' for r in w])} weeks (weeks 75-78, March 2026 sell-off: wheel LONG throughout, Rs{sum(float(r['net_rs']) for r in w[75:79]):+,.0f} over those 4 weeks).")
    lots = Counter(r["lot_size"] for r in csv.DictReader(open(wc.DATA / "wheel_lot_sizes.csv")))
    L.append(f"6 LOT SIZE (Upstox contract lists, expiries with a list fetched): {dict(lots)}; 75 is used for every week as instructed, so rupee figures are for 75 units, not true lots.")
    pr = np.array([float(r["premium_rs"]) for r in trad]) / wc.LOT
    L.append(f"7 PREMIUM CHECK: mean premium sold {pr.mean():.1f} pts/unit (median {np.median(pr):.1f}, max {pr.max():.1f}); fills are candle opens minus Rs0.20, no bid/ask in the data; "
             f"illiquid far-OTM contracts may not trade at those prices.")
    (OUT / "wheel_review.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def max_run(flags):
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


if __name__ == "__main__":
    main()
