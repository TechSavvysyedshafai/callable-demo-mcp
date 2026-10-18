"""Run gate G0 and trials T1, T2, T3 ONCE (rules: research/RESULTS.md "Planned ... branch claude/employee-settlement"; study text
docs/ideas/IDEAS_BATCH3_SETTLEMENT_2026-10-18.md). No arguments change any rule. Writes research/settlement/results/*.
With --record it also appends the batch and the 3 trials to the loop's append-only trial ledger (once; refuses a second time).
  python research/settlement/settlement_run.py [--record]"""

import argparse
import csv
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settlement_core as sc  # noqa: E402

OUT = HERE / "results"
MD = HERE.parent.parent / "docs" / "ideas" / "IDEAS_BATCH3_SETTLEMENT_2026-10-18.md"


def rs(x):
    return "n/a" if x != x else f"{x:+,.0f}"


def run() -> dict:
    bars, closes, expiries = sc.load_index()
    g0 = sc.gate_g0(bars, closes, expiries)
    res = {"expiries": len(expiries), "g0": {k: v for k, v in g0.items() if k != "days"}}
    if g0["stop"]:
        res["stopped"] = True
        return res
    t1 = sc.run_straddle_trial(bars, closes, expiries, wings=False)
    t2 = sc.run_straddle_trial(bars, closes, expiries, wings=True)
    res["t1"] = {"summary": sc.summarise_trial(t1["rows"], t1["skipped"], len(expiries)), "skipped": [(str(d), r) for d, r in t1["skipped"]]}
    res["t2"] = {"summary": sc.summarise_trial(t2["rows"], t2["skipped"], len(expiries)), "skipped": [(str(d), r) for d, r in t2["skipped"]]}
    t3 = sc.run_pin_test(bars, closes, expiries)
    res["t3"] = {k: v for k, v in t3.items() if k not in ("days", "skipped")}
    res["t3"]["skipped"] = [(str(d), r) for d, r in t3["skipped"]]
    OUT.mkdir(exist_ok=True)
    for name, t in (("t1", t1), ("t2", t2)):
        with (OUT / f"{name}_days.csv").open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["expiry", "S0", "K", "A", "S1", "straddle_px", "sigma_pts", "gross_mid_rs", "net_0.10", "net_0.20", "net_0.30", "fees_0.20"])
            for r in t["rows"]:
                w.writerow([r["expiry"], r["S0"], r["K"], r["A"], r["S1"], r["straddle_px"], round(r["sigma_pts"], 6), r["gross_mid_rs"],
                            r["net_0.10"], r["net_0.20"], r["net_0.30"], r["fees_0.20"]])
    with (OUT / "t3_days.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["expiry", "K0", "A", "K_max_oi", "dist_max", "n_strikes", "mean_dist_all_strikes", "dist_spot_strike", "max_total_oi", "tie"])
        for d in t3["days"]:
            w.writerow([d["expiry"], d["K0"], d["A"], d["K_max_oi"], d["dist_max"], d["n_strikes"], round(float(d["dists"].mean()), 6),
                        d["dist_spot_strike"], d["max_oi"], d["tie"]])
    return res


def record(res: dict) -> None:
    sys.path.insert(0, str(HERE.parent / "ideas" / "loop"))
    import trial_ledger as tl
    if tl.trial_for("B3-01") is not None:
        raise SystemExit("B3 trials are already in the ledger; refusing to append twice")
    text = MD.read_text()
    rules = {i: next(line for line in text.splitlines() if line.startswith(f"T{n} ")) for n, i in ((1, "B3-01"), (2, "B3-02"), (3, "B3-03"))}
    hashes = {i: hashlib.sha256(r.encode()).hexdigest() for i, r in rules.items()}
    prior = tl.total_trials()
    alpha = tl.batch_alpha(prior, 3)
    assert prior == 10 and abs(alpha - sc.ALPHA) < 1e-12, (prior, alpha)
    tl.append({"event": "batch_start", "batch": 3, "prior_trials": prior, "n_ideas": 3, "alpha": alpha, "md_file": MD.name,
               "md_sha256": hashlib.sha256(MD.read_bytes()).hexdigest(), "ideas": hashes, "source": "Task 7 (research/settlement)"})
    names = {"B3-01": ("t1", "T1 short straddle into the average"), "B3-02": ("t2", "T2 defined-risk straddle (100-point wings)"),
             "B3-03": ("t3", "T3 pin test")}
    for i, (k, nm) in names.items():
        r = res[k]["summary"] if k != "t3" else res[k]
        if k == "t3":
            ev = {"n_trades": r["n"], "mean_net": None, "boot_p": None, "null_p": r["p"], "verdict": "SURVIVES" if r["pass"] else "REJECT"}
        else:
            ev = {"n_trades": r["n"], "mean_net": r["mean_net_0.20"], "boot_p": r["boot_p"], "null_p": None, "verdict": r["verdict"],
                  "checks": r["checks"]}
        tl.append({"event": "trial", "idea_id": i, "batch": 3, "rule_hash": hashes[i], "alpha": alpha, "name": nm,
                   "source": "research/settlement/results/settlement_results.json", **ev})


def report(res: dict) -> str:
    g = res["g0"]
    L = [f"G0: n={g['n']} expiry days, std(A-S0)={g['std_A_minus_S0']:.2f}, std(S1-S0)={g['std_S1_minus_S0']:.2f}, ratio={g['ratio']:.3f} "
         f"(theory 0.58 if the close is a 30-minute average, 1.0 if last print; STOP above 0.85) -> {'STOP' if g['stop'] else 'PASS (continue)'}; skipped {g['skipped']}"]
    if res.get("stopped"):
        return "\n".join(L)
    for k in ("t1", "t2"):
        s, sk = res[k]["summary"], res[k]["skipped"]
        L += ["", f"{k.upper()}: n={s['n']} of {s['n_expiries']} expiries (skipped {s['skipped']}: {sorted(set(r for _, r in sk))})",
              f"  mean net/trade Rs: 0.10 {rs(s['mean_net_0.10'])} | 0.20 {rs(s['mean_net_0.20'])} | 0.30 {rs(s['mean_net_0.30'])}; mean before costs (mid, no fees) {rs(s['mean_gross_mid'])}; mean fees at 0.20 {rs(s['mean_fees_0.20'])}",
              f"  bootstrap p (0.20) {s['boot_p']:.4f} (0.10: {s['boot_p_by_slip']['0.10']:.4f}, 0.30: {s['boot_p_by_slip']['0.30']:.4f}; before costs {s['boot_p_gross_mid']:.4f}); alpha {sc.ALPHA:.5f}",
              f"  halves (split {s['midpoint']}): first n={s['first_n']} mean {rs(s['first_mean'])} | second n={s['second_n']} mean {rs(s['second_mean'])}",
              f"  worst trade {rs(s['worst_trade'])}; best {rs(s['best_trade'])}; max drawdown {rs(s['max_drawdown'])}; total net {rs(s['total_net'])}; win rate {s['win_rate']:.1%}",
              f"  calibration (straddle px / model Asian straddle 0.58*sigma*sqrt(T)): {s['calibration']['ratio_literal']:.3f} pooled "
              f"(mean of daily ratios {s['calibration']['mean_of_daily_ratios_literal']:.3f}, median {s['calibration']['median_daily_ratio_literal']:.3f}); "
              f"vs 0.798x that value: {s['calibration']['ratio_with_sqrt2pi']:.3f}; mean px {s['calibration']['mean_straddle_px']:.1f}, mean model {s['calibration']['mean_model_literal']:.1f}",
              f"  checks {s['checks']} -> {s['verdict']}"]
    t = res["t3"]
    L += ["", f"T3: n={t['n']} days (skipped {len(t['skipped'])}: {sorted(set(r for _, r in t['skipped']))}); mean |A-K_maxOI| {t.get('obs_mean_dist', float('nan')):.1f} pts, "
          f"random-strike mean {t.get('null_mean_dist', float('nan')):.1f} (expected {t.get('expected_random_dist', float('nan')):.1f}), spot-nearest strike {t.get('mean_dist_spot_strike', float('nan')):.1f}; p={t['p']:.4f} vs {sc.ALPHA:.5f} -> {'PASS' if t['pass'] else 'REJECT'}",
          f"  max-OI strike equals the spot strike on {t.get('share_max_oi_is_spot_strike', float('nan')):.0%} of days; mean |K_maxOI - K0| {t.get('mean_abs_maxoi_minus_spotstrike', float('nan')):.0f}; settlement within 25 pts of the max-OI strike on {t.get('share_exact_pin', float('nan')):.0%}; ties {t.get('ties')}; mean strikes/day {t.get('mean_strikes', float('nan')):.1f}"]
    return "\n".join(L)


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--record", action="store_true", help="append the batch and 3 trials to the loop ledger")
    a = a.parse_args()
    res = run()
    OUT.mkdir(exist_ok=True)
    (OUT / "settlement_results.json").write_text(json.dumps(res, indent=1, default=str))
    txt = report(res)
    (OUT / "settlement_results.txt").write_text(txt + "\n")
    print(txt)
    if a.record and not res.get("stopped"):
        record(res)
        print("\nledger: recorded batch 3 (B3-01..03)")
