"""Run one declared batch of NEW ideas, once each, with the Task 5 pass rule.

  python batch_runner.py --batch 2 --md docs/ideas/IDEAS_BATCH2_2026-10-25.md

Before anything is run it checks, and refuses (running NOTHING) if any check fails:
  * the ledger hash chain is intact and the registry matches the ledger;
  * the batch has 1..10 ideas, each registered as `proposed` (or already run, when resuming a crashed batch);
  * every idea's rule still hashes to the value stored when it was registered (a changed rule = refused);
  * the dated markdown file docs/ideas/IDEAS_BATCH<N>_<YYYY-MM-DD>.md exists, is not dated in the future, and names every idea id and the first 12
    characters of its rule hash (so the written declaration and the registered rule are the same thing).
Then it writes `batch_start` to the ledger FIRST (alpha = 0.05 / (all trials ever + this batch), fixed before any result exists), runs each idea once,
writes one `trial` line per idea, and moves each idea to rejected (not SURVIVES) or forward (SURVIVES, forward_since = run date).
There are no tuning options: the only inputs are the batch number, the declaration file, and (for tests) a data folder."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import loop_config as cfg  # noqa: E402
import loop_stats as ls  # noqa: E402
import registry as reg  # noqa: E402
import rule_engine as rules  # noqa: E402
import trial_ledger as tl  # noqa: E402
import forced_trader_ideas as fi  # noqa: E402

MD_RE = re.compile(r"^IDEAS_BATCH(\d+)_(\d{4}-\d{2}-\d{2})\.md$")


class BatchRefused(Exception):
    pass


def load_dev_data(dev_dir: Path, need: dict) -> tuple:
    """Dev files only (the same ones Task 5 used). Refuses any folder whose path mentions the hidden holdout."""
    if "holdout" in str(dev_dir).lower():
        raise BatchRefused("refusing to read a holdout folder")
    f = {k: Path(dev_dir) / v for k, v in cfg.DEV_FILES.items()}
    miss = [str(f[k]) for k in ("daily", "vix", "m5") if need.get(k) and not f[k].exists()]
    if miss:
        raise BatchRefused(f"dev data not found: {miss}. Download it with research/upstox/fetch_upstox.py first.")
    d = fi.load_daily(f["daily"]) if need.get("daily") else None
    v = fi.load_vix(f["vix"]) if need.get("vix") else None
    m = fi.load_5min(f["m5"]) if need.get("m5") else None
    return d, v, m


def preflight(batch: int, md_path: Path, paths, today: date) -> list:
    """All the refusal checks. Returns the ideas to run (those without a trial yet) and raises BatchRefused on any problem."""
    pr = reg.problems(paths)
    if pr:
        raise BatchRefused("registry/ledger problems: " + "; ".join(pr))
    ideas = reg.batch_of(batch, paths)
    if not 1 <= len(ideas) <= cfg.MAX_BATCH:
        raise BatchRefused(f"batch {batch} has {len(ideas)} registered ideas (need 1 to {cfg.MAX_BATCH})")
    for r in ideas:
        if r["rule"].get("kind") not in ("daily", "intraday"):
            raise BatchRefused(f"{r['id']}: only daily/intraday rules can be run by the batch runner")
        if rules.rule_hash(r["rule"]) != r["rule_hash"]:
            raise BatchRefused(f"{r['id']}: the rule changed after it was registered (hash differs). A changed rule is a new idea with a new id.")
        done = tl.trial_for(r["id"], paths) is not None
        if r["status"] != "proposed" and not done:
            raise BatchRefused(f"{r['id']} has status {r['status']}, expected proposed")
        rules.validate_rule(r["rule"])
    if len({r["cost"] for r in ideas}) != 1:
        raise BatchRefused("ideas in one batch must share one cost")
    m = MD_RE.match(md_path.name)
    if not m or int(m.group(1)) != batch:
        raise BatchRefused(f"declaration file must be named IDEAS_BATCH{batch}_<YYYY-MM-DD>.md, got {md_path.name}")
    if date.fromisoformat(m.group(2)) > today:
        raise BatchRefused("the declaration file is dated in the future")
    if not md_path.exists():
        raise BatchRefused(f"declaration file {md_path} not found: write it BEFORE running")
    text = md_path.read_text()
    for r in ideas:
        if r["id"] not in text or r["rule_hash"][:12] not in text:
            raise BatchRefused(f"{md_path.name} does not name {r['id']} together with rule hash {r['rule_hash'][:12]}")
    return [r for r in ideas if tl.trial_for(r["id"], paths) is None]


def run_batch(batch: int, md_path: Path, paths=None, today: date | None = None, data: tuple | None = None) -> list:
    paths = paths or cfg.PATHS
    today = today or date.today()
    md_path = Path(md_path)
    todo = preflight(batch, md_path, paths, today)
    ideas = reg.batch_of(batch, paths)
    started = [e for e in tl.events("batch_start", paths) if e["batch"] == batch]
    if started:
        alpha = started[0]["alpha"]  # resuming: the alpha fixed at the start stays
        if abs(alpha - tl.batch_alpha(started[0]["prior_trials"], len(ideas))) > 1e-15:
            raise BatchRefused("batch size changed since the batch started")
    else:
        prior = tl.total_trials(paths)
        alpha = tl.batch_alpha(prior, len(ideas))
        tl.append({"event": "batch_start", "batch": batch, "prior_trials": prior, "n_ideas": len(ideas), "alpha": alpha, "cost": ideas[0]["cost"],
                   "md_file": md_path.name, "md_sha256": hashlib.sha256(md_path.read_bytes()).hexdigest(),
                   "ideas": {r["id"]: r["rule_hash"] for r in ideas}}, paths, today)
    if not todo:
        return []
    need = {"daily": False, "vix": False, "m5": False}
    for r in todo:
        for k, v in rules.needs(r["rule"]).items():
            if k in need:
                need[k] = need[k] or v
    d, v, m = data if data is not None else load_dev_data(paths.dev_dir, need)
    out = []
    for r in todo:
        sc = rules.scan(r["rule"], d, v, m)
        t = rules.to_trades(int(r["id"].split("-")[1]), r["name"], sc)
        res = ls.evaluate(t, r["cost"], alpha)
        res["id"] = r["id"]
        tl.append({"event": "trial", "idea_id": r["id"], "batch": batch, "rule_hash": r["rule_hash"], "alpha": alpha, "verdict": res["verdict"],
                   "n_trades": res["n_trades"], "mean_net": res["mean_net"], "boot_p": res["boot_p"], "null_p": res["null_p"], "checks": res["checks"]},
                  paths, today)
        stats = {k: res[k] for k in ("n_trades", "mean_net", "mean_gross", "boot_p", "null_p", "first_n", "first_mean", "second_n", "second_mean", "win_rate", "window", "alpha", "cost")}
        reg.set_status(r["id"], "tested", f"batch {batch} run once, verdict {res['verdict']}", paths, today, verdict=res["verdict"], dev_stats=stats,
                       dev_max_drawdown=res["dev_max_drawdown"])
        if res["verdict"] == "SURVIVES":
            reg.set_status(r["id"], "forward", f"passed at alpha {alpha:.5f}; paper forward test starts after {today}", paths, today, forward_since=str(today))
        else:
            reg.set_status(r["id"], "rejected", f"{res['verdict']} at alpha {alpha:.5f}", paths, today, retire_reason=f"{res['verdict']} at the batch test")
        out.append(res)
    _write_results(batch, out, alpha, paths, today)
    return out


def _pct(x) -> str:
    return "n/a" if x != x else f"{x * 100:+.3f}%"


def _write_results(batch: int, out: list, alpha: float, paths, today: date) -> None:
    paths.results.mkdir(parents=True, exist_ok=True)
    (paths.results / f"batch{batch}_results.json").write_text(json.dumps({"batch": batch, "run_on": str(today), "alpha": alpha, "results": out}, indent=1, default=str))
    L = [f"Batch {batch}, run {today}. Alpha for this batch = 0.05 / {int(round(0.05 / alpha))} trials = {alpha:.5f}.", "",
         "| id | Idea | Trades | Mean net/trade | Mean at zero cost | Bootstrap p | Null p | First half | Second half | Verdict |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in out:
        L.append(f"| {r['id']} | {r['name']} | {r['n_trades']} | {_pct(r['mean_net'])} | {_pct(r['mean_gross'])} | {r['boot_p']:.4f} | {r['null_p']:.4f} | "
                 f"{r['first_n']}, {_pct(r['first_mean'])} | {r['second_n']}, {_pct(r['second_mean'])} | **{r['verdict']}** |")
    (paths.results / f"batch{batch}_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--batch", type=int, required=True)
    a.add_argument("--md", required=True, help="the dated docs/ideas/IDEAS_BATCH<N>_<date>.md written before running")
    a.add_argument("--data-dir", help="dev data folder (default research/data)")
    a = a.parse_args()
    p = cfg.Paths()
    if a.data_dir:
        p.dev_dir = Path(a.data_dir)
    try:
        run_batch(a.batch, Path(a.md), p)
    except (BatchRefused, reg.RegistryError, tl.LedgerTampered, rules.RuleError) as e:
        sys.exit(f"REFUSED: {e}")


if __name__ == "__main__":
    main()
