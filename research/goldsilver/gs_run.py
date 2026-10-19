"""Run the ONE pre-registered Batch 6 trial (B6-01, gold vs silver ratio pair) plus the listed information-only checks, ONCE.
Rules: research/RESULTS.md ("Planned (pre-registered 2026-10-19, branch claude/employee-goldsilver ..."); study text
docs/ideas/IDEAS_BATCH6_GOLD_SILVER_PAIR_2026-10-19.md. No argument changes a rule.
Writes research/goldsilver/results/*. Does NOT touch research/ideas/loop/ledger_loop.jsonl (the project manager appends the trial).
  python research/goldsilver/gs_run.py"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gs_core as gc  # noqa: E402

OUT = HERE / "results"
MD = HERE.parent.parent / "docs" / "ideas" / "IDEAS_BATCH6_GOLD_SILVER_PAIR_2026-10-19.md"
LOOKBACKS, ENTRIES = (40, 60, 90), (1.5, 2.0, 2.5)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plateau(grid: dict, base_key: str = "60_2.0") -> dict:
    """Pre-registered rule: plateau if >= 6 of the 8 neighbours share the sign of the base cell's mean net AND no neighbour with
    >= 15 trades has boot p < alpha while the base does not; otherwise spike."""
    base = grid[base_key]
    nb = {k: v for k, v in grid.items() if k != base_key}
    sign = np.sign(base["mean_net"])
    same = sum(1 for v in nb.values() if np.sign(v["mean_net"]) == sign)
    better = [k for k, v in nb.items() if v["n_trades"] >= gc.MIN_TRADES and v["boot_p"] < gc.ALPHA] if not base["boot_p"] < gc.ALPHA else []
    return {"same_sign_neighbours": int(same), "of": len(nb), "neighbours_that_pass_boot_while_base_does_not": better,
            "label": "plateau" if (same >= 6 and not better) else "spike",
            "cells_below_15_trades": sorted(k for k, v in grid.items() if v["n_trades"] < gc.MIN_TRADES)}


def main() -> None:
    df, skipped = gc.load()
    sim = gc.simulate(df)
    trades = sim["trades"]
    main_res = gc.evaluate(df)
    grid = {}
    for lb in LOOKBACKS:
        for en in ENTRIES:
            grid[f"{lb}_{en:.1f}"] = main_res if (lb, en) == (gc.LOOKBACK, gc.ENTRY) else gc.evaluate(df, lb, en)
    # the 60 / 2.0 grid cell is B6-01 by construction; re-evaluate independently to prove they are identical
    again = gc.evaluate(df, 60, 2.0)
    assert json.dumps(again, sort_keys=True, default=str) == json.dumps(main_res, sort_keys=True, default=str), "grid base cell differs from B6-01"
    res = {"trial_id": "B6-01", "trial_number_overall": 16, "alpha": gc.ALPHA, "study_md": MD.name, "study_md_sha256": sha(MD),
           "code_sha256": {p.name: sha(p) for p in sorted(HERE.glob("gs_*.py"))},
           "keys": {"GOLDBEES": "NSE_EQ|INF204KB17I5", "SILVERBEES": "NSE_EQ|INF204KC1402"},
           "sample": {"first_common_date": str(df["date"].iloc[0].date()), "last_common_date": str(df["date"].iloc[-1].date()),
                      "n_common_days": len(df), "first_signal_eligible_row": gc.LOOKBACK - 1,
                      "first_signal_date": str(df["date"].iloc[gc.LOOKBACK - 1].date()), "span_years": float((df["date"].iloc[-1] - df["date"].iloc[0]).days / 365.25)},
           "skipped": skipped, "primary": main_res, "grid": grid, "plateau": plateau(grid),
           "z_summary": {"n_defined": int(np.isfinite(sim["z"]).sum()), "n_days_z_ge_2": int((sim["z"] >= 2).sum()), "n_days_z_le_minus_2": int((sim["z"] <= -2).sum()),
                         "max_abs_z": float(np.nanmax(np.abs(sim["z"])))},
           "trades": trades}
    OUT.mkdir(exist_ok=True)
    (OUT / "goldsilver_results.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    import csv
    with open(OUT / "goldsilver_trades.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["signal_date", "entry_date", "exit_date", "direction(+1 buy gold/sell silver)", "reason", "z_signal", "hold_trading_days", "cal_days", "gross", "net"])
        net = gc.net_returns(trades)
        for t, n in zip(trades, net):
            w.writerow([t["signal_date"], t["entry_date"], t["exit_date"], t["direction"], t["reason"], f"{t['z_signal']:.4f}", t["hold"], t["cal_days"], f"{t['gross']:.6f}", f"{n:.6f}"])
    p = main_res
    print(f"B6-01: trades {p['n_trades']}  mean net {p['mean_net']*100:+.3f}%  zero-cost {p['mean_gross']*100:+.3f}%  boot p {p['boot_p']:.4f}  null p {p['null_p']:.4f}  verdict {p['verdict']}")
    print(f"halves {p['first_n']}/{p['second_n']}: {p['first_mean']*100:+.3f}% / {p['second_mean']*100:+.3f}%  worst {p['worst_net']*100:+.2f}%  maxDD {p['max_drawdown']*100:.2f}%")
    for k, v in grid.items():
        print(f"  {k:>8}: n={v['n_trades']:>3} mean {v['mean_net']*100:+.3f}% zero-cost {v['mean_gross']*100:+.3f}% boot p {v['boot_p']:.3f} null p {v['null_p']:.3f} halves {v['first_mean']*100:+.2f}/{v['second_mean']*100:+.2f}")
    print("plateau:", res["plateau"])


if __name__ == "__main__":
    main()
