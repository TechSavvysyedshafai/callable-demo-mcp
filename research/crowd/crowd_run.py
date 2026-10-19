"""Run the ONE pre-registered trial B5-01 (crowd positioning from option OI) plus the information-only checks, write results/crowd_results.{json,md}
and results/crowd_weeks.csv.   python research/crowd/crowd_run.py      No arguments: nothing can be tuned from the command line.
Does NOT touch research/ideas/loop/ledger_loop.jsonl (the project manager appends the trial after merging); the trial record is in the JSON."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crowd_core as cc  # noqa: E402

OUT = HERE / "results"


def pct(x):
    return "n/a" if x != x else f"{x * 100:+.3f}%"


def code_hash() -> str:
    return hashlib.sha256((HERE / "crowd_core.py").read_bytes()).hexdigest()[:12]


def lot_sizes() -> dict:
    f = cc.DATA / "crowd_lot_sizes.csv"
    if not f.exists():
        return {}
    out: dict = {}
    for r in csv.DictReader(f.open()):
        out[r["lot_size"]] = out.get(r["lot_size"], 0) + 1
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    bars, closes, expiries = cc.wc.load_index()
    assert bars["date"].max() <= cc.pd.Timestamp("2026-04-16 23:59"), "index data must be dev-only"
    by_ts = bars.set_index("date")
    plans = cc.make_plans(bars, expiries)
    loader = cc.file_loader()
    sig = cc.signal_weeks(plans, loader, cc.WINDOW)
    primary = cc.evaluate(cc.build_trades(plans, sig, by_ts, closes))
    info = {"zero_cost": {"mean_net": primary["mean_zero_cost"], "boot_p_zero_cost": primary.get("boot_p_zero_cost"), "null_p_zero_cost": primary.get("null_p_zero_cost"),
                          "halves_zero_cost": primary.get("halves_zero_cost")}}
    info["opposite_direction"] = cc.evaluate(cc.build_trades(plans, sig, by_ts, closes, flip=True))
    sig150 = cc.signal_weeks(plans, loader, 150)
    tr150 = cc.build_trades(plans, sig150, by_ts, closes)
    info["window_150"] = cc.evaluate(tr150)
    info["window_150"]["skips"] = cc.skip_summary(sig150)
    for d in (1, 2):
        info[f"entry_plus_{d}_bar"] = cc.evaluate(cc.build_trades(plans, sig, by_ts, closes, delay=d))
    skips = cc.skip_summary(sig)
    nst = [s["n_strikes"] for s in sig if s.get("x") is not None]
    cov = {"weeks_with_x": len(nst), "strikes_used_min": int(min(nst)), "strikes_used_median": float(np.median(nst)), "strikes_used_max": int(max(nst)),
           "weeks_with_fewer_than_9_strikes": [str(s["expiry"]) for s in sig if s.get("x") is not None and s["n_strikes"] < 9]}
    res = {"trial": {"id": cc.TRIAL_ID, "trial_number": cc.TOTAL_TRIALS, "alpha": cc.ALPHA, "study": "IDEAS_BATCH5_CROWD_POSITIONING", "code_hash": code_hash(),
                     "verdict": primary["verdict"], "n_trades": primary["n_trades"], "mean_net": primary["mean_net"], "boot_p": primary["boot_p"], "null_p": primary["null_p"],
                     "ledger_note": "NOT appended to the loop ledger (the project manager appends the trial after merging)"},
           "primary": primary, "info": info, "skips": skips, "coverage": cov, "lot_sizes_from_contract_lists": lot_sizes(),
           "window": [str(expiries[0]), str(expiries[-1])], "dev_cutoff": str(cc.DEV_CUTOFF)}
    (OUT / "crowd_results.json").write_text(json.dumps(res, indent=1, default=str))
    with (OUT / "crowd_weeks.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["k", "expiry", "entry_day", "spot", "n_strikes", "call_oi", "put_oi", "pcr", "x", "z", "direction", "skipped"])
        for s in sig:
            w.writerow([s["k"], s["expiry"], s["entry_day"], s["spot"], s["n_strikes"], s["call_oi"], s["put_oi"], s.get("pcr", ""), s["x"] if s["x"] is not None else "",
                        s["z"] if s["z"] is not None else "", s["direction"], s["skipped"] or ""])

    prim_tr = cc.build_trades(plans, sig, by_ts, closes)["trades"]
    with (OUT / "crowd_trades.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["expiry", "entry_day", "direction", "z", "entry", "exit", "gross_long_ret", "net_ret", "net_rs"])
        for t in prim_tr:
            w.writerow([t["expiry"], t["entry_day"], t["direction"], repr(t["z"]), t["entry"], t["exit"], repr(t["gross"]), repr(t["net_ret"]), repr(t["net_rs"])])

    def row(name, r):
        return (f"| {name} | {r['n_trades']} | {pct(r['mean_net'])} | {pct(r['mean_zero_cost'])} | {r['boot_p']:.4f} | {r.get('null_p', float('nan')):.4f} | "
                f"{r.get('first_n', 0)}, {pct(r.get('first_mean', float('nan')))} | {r.get('second_n', 0)}, {pct(r.get('second_mean', float('nan')))} | {r['verdict']} |")
    L = ["| Run | Trades | Mean net/trade | Mean at zero cost | Bootstrap p | Null p | First half (n, mean) | Second half (n, mean) | Verdict |", "|---|---|---|---|---|---|---|---|---|",
         row("**B5-01 (the trial)**", primary), row("info: opposite direction", info["opposite_direction"]), row("info: strike window +/-150", info["window_150"]),
         row("info: entry +1 bar", info["entry_plus_1_bar"]), row("info: entry +2 bars", info["entry_plus_2_bar"])]
    (OUT / "crowd_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print("\nprimary:", json.dumps({k: v for k, v in primary.items() if k not in ("lost",)}, default=str))
    print("\nskips:", json.dumps(skips, default=str))
    print("coverage:", json.dumps(cov, default=str))
    print("lot sizes:", lot_sizes())


if __name__ == "__main__":
    main()
