"""Run the 10 pre-registered ideas ONCE, write results/ideas_batch1_results.{json,md} and the trial ledger.
  python research/ideas/evaluate_ideas.py
No arguments: nothing can be tuned from the command line."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import forced_trader_ideas as fi  # noqa: E402

OUT = HERE / "results"
LEDGER = HERE / "ledger_ideas.jsonl"


def log_trials(results: list, ch: str) -> None:
    seen = set()
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            r = json.loads(line)
            seen.add((r["idea"], r["code_hash"]))
    with LEDGER.open("a") as f:
        for r in results:
            if (r["idea"], ch) in seen:
                continue
            f.write(json.dumps({"study": "IDEAS_BATCH1", "idea": r["idea"], "strategy": r["name"], "code_hash": ch, "trial": r["idea"],
                                "n_trades": r["n_trades"], "mean_net": round(r["mean_net"], 6), "boot_p": r["boot_p"], "null_p": r["null_p"],
                                "verdict": r["verdict"]}) + "\n")


def pct(x):
    return "n/a" if x != x else f"{x * 100:+.3f}%"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    d, v, m = fi.load_daily(), fi.load_vix(), fi.load_5min()
    trades = fi.run_all()
    results = [fi.evaluate_idea(t) for t in trades]
    info = {"idea2_intraday_leg": fi.evaluate_idea(fi.idea2_intraday_info(d)),
            "delay_idea3": fi.delay_check_intraday(m, 3), "delay_idea5": fi.delay_check_idea5(d, v),
            "delay_idea6": fi.delay_check_intraday(m, 6), "delay_idea7": fi.delay_check_intraday(m, 7),
            "daily_rows": len(d), "vix_rows": len(v), "bars_5min": len(m),
            "expiry_days_found": int(len(fi.expiry_rows(d)))}
    ch = fi.code_hash()
    log_trials(results, ch)
    (OUT / "ideas_batch1_results.json").write_text(json.dumps({"code_hash": ch, "results": results, "info": info}, indent=1, default=str))
    L = ["| # | Idea | Trades | Mean net/trade | Mean at zero cost | Bootstrap p | Null p | First half (n, mean) | Second half (n, mean) | Verdict |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        L.append(f"| {r['idea']} | {r['name']} | {r['n_trades']} | {pct(r['mean_net'])} | {pct(r['mean_gross'])} | {r['boot_p']:.4f} | {r['null_p']:.4f} | "
                 f"{r['first_n']}, {pct(r['first_mean'])} | {r['second_n']}, {pct(r['second_mean'])} | **{r['verdict']}** |")
    (OUT / "ideas_batch1_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print("\nzero-cost p (info): " + "; ".join(f"#{r['idea']} boot {r['boot_p_zero_cost']:.4f} null {r['null_p_zero_cost']:.4f}" for r in results))
    print("skipped:", {r["idea"]: r["skipped"] for r in results}, "windows:", {r["idea"]: r["window"] for r in results})
    print("info:", json.dumps(info, default=str))


if __name__ == "__main__":
    main()
