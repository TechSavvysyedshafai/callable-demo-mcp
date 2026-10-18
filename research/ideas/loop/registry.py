"""The idea registry: one line per idea in registry.jsonl (id, machine-readable rule, story, created, status, plus its hash).
Every change is also written to the hash-chained ledger, which is the record the rule hash is checked against.

  python registry.py list | show ID | check | seed | register FILE.json [--allow-variant] | md-row ID

Statuses: proposed -> tested -> rejected | forward -> promoted -> retired (forward may also be retired by hand). Rejected and retired are final.
Changing a rule never edits an old idea: it is a NEW idea (a new trial that counts), registered with its own id."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import loop_config as cfg  # noqa: E402
import rule_engine as re_  # noqa: E402
import trial_ledger as tl  # noqa: E402

STATUSES = ("proposed", "tested", "rejected", "forward", "promoted", "retired")
MOVES = {"proposed": {"tested"}, "tested": {"rejected", "forward"}, "forward": {"promoted", "retired"}, "promoted": {"retired"}, "rejected": set(), "retired": set()}
ID_RE = re.compile(r"^B\d{1,3}-\d{2}$")


class RegistryError(Exception):
    pass


def load(paths=None) -> list:
    p = (paths or cfg.PATHS).registry
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def _save(rows: list, paths=None) -> None:
    p = (paths or cfg.PATHS).registry
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    os.replace(tmp, p)


def get(idea_id: str, paths=None) -> dict:
    for r in load(paths):
        if r["id"] == idea_id:
            return r
    raise RegistryError(f"no idea {idea_id}")


def by_status(status: str, paths=None) -> list:
    return [r for r in load(paths) if r["status"] == status]


def batch_of(batch: int, paths=None) -> list:
    return [r for r in load(paths) if r["batch"] == batch]


# ----------------------------------------------------------------------------------------------- registering
def register(idea_id: str, batch: int, name: str, story: str, rule: dict, cost: float = cfg.DEFAULT_COST,
             allow_variant: bool = False, paths=None, on: date | None = None) -> dict:
    """Add a PROPOSED idea. Must be done (and the dated IDEAS_BATCH md written) before the batch is run."""
    rows = load(paths)
    if not ID_RE.match(idea_id) or int(idea_id[1:].split("-")[0]) != batch:
        raise RegistryError(f"id {idea_id!r} must look like B{batch}-01")
    if any(r["id"] == idea_id for r in rows):
        raise RegistryError(f"{idea_id} already exists")
    re_.validate_rule(rule)
    h, fam = re_.rule_hash(rule), re_.family_hash(rule)
    for r in rows:
        if r["rule_hash"] == h:
            raise RegistryError(f"same rule as {r['id']}: not a new idea")
    variants = [r["id"] for r in rows if r.get("family_hash") == fam]
    if variants and not allow_variant:
        raise RegistryError(f"looks like a variant of {variants} (same rule apart from numbers). A changed threshold is a NEW trial that counts; "
                            f"register it with allow_variant=True / --allow-variant if you really mean it")
    if sum(1 for r in rows if r["batch"] == batch) >= cfg.MAX_BATCH:
        raise RegistryError(f"batch {batch} already has {cfg.MAX_BATCH} ideas")
    if any(r["batch"] == batch and r["cost"] != cost for r in rows):
        raise RegistryError("all ideas in a batch share one cost")
    if tl.events("batch_start", paths) and any(e["batch"] == batch for e in tl.events("batch_start", paths)):
        raise RegistryError(f"batch {batch} was already run; new ideas go in a new batch")
    row = {"id": idea_id, "batch": batch, "name": name, "story": story, "rule": rule, "rule_hash": h, "family_hash": fam, "cost": cost,
           "created": str(on or date.today()), "status": "proposed", "variant_of": variants, "verdict": None, "dev_stats": None,
           "dev_max_drawdown": None, "forward_since": None, "promoted_on": None, "retired_on": None, "retire_reason": None}
    tl.append({"event": "register", "idea_id": idea_id, "batch": batch, "rule_hash": h, "status": "proposed", "cost": cost, "variant_of": variants},
              paths, on)
    _save(rows + [row], paths)
    return row


def set_status(idea_id: str, new: str, reason: str, paths=None, on: date | None = None, **fields) -> dict:
    rows = load(paths)
    r = next((x for x in rows if x["id"] == idea_id), None)
    if r is None:
        raise RegistryError(f"no idea {idea_id}")
    if new not in MOVES.get(r["status"], ()):
        raise RegistryError(f"{idea_id}: {r['status']} -> {new} is not allowed")
    tl.append({"event": "status", "idea_id": idea_id, "from": r["status"], "to": new, "reason": reason, "rule_hash": r["rule_hash"]}, paths, on)
    r.update(fields)
    r["status"] = new
    _save(rows, paths)
    return r


def problems(paths=None) -> list:
    """Cross-check the registry file against the ledger. Empty list = consistent."""
    out = []
    try:
        tl.verify(paths)
    except tl.LedgerTampered as e:
        return [str(e)]
    evs = tl.read(paths)
    for r in load(paths):
        i = r["id"]
        if re_.rule_hash(r["rule"]) != r["rule_hash"]:
            out.append(f"{i}: rule no longer matches the hash stored at registration (rule edited)")
        reg = [e for e in evs if e["event"] == "register" and e["idea_id"] == i]
        if len(reg) != 1:
            out.append(f"{i}: not registered exactly once in the ledger")
        elif reg[0]["rule_hash"] != r["rule_hash"]:
            out.append(f"{i}: registry hash differs from the ledger hash")
        last = [e for e in evs if e["event"] in ("register", "status") and e["idea_id"] == i]
        if last and (last[-1].get("to") or last[-1].get("status")) != r["status"]:
            out.append(f"{i}: registry status {r['status']} differs from the ledger")
    return out


# ----------------------------------------------------------------------------------------------- seed batch 1
RULES1 = {
    1: {"entry": "close of the 2nd-last trading day of a month", "exit": "close of the 3rd trading day of the next month", "direction": 1},
    2: {"entry": "close", "exit": "next open", "direction": 1, "leg": "overnight"},
    3: {"gap": 0.007, "entry": "open", "exit": "close", "direction": "against the gap"},
    4: {"drop": 0.02, "entry": "next open", "exit": "next close", "direction": 1},
    5: {"vix_rise": 0.15, "hold_days": 3, "entry": "close", "direction": 1},
    6: {"signal": "14:15 to 15:15", "entry": "15:15", "exit": "15:25 close", "direction": "with signal"},
    7: {"signal": "first 30 minutes", "entry": "09:45", "exit": "15:15", "direction": "with signal"},
    8: {"entry": "close before a market holiday", "exit": "next open", "direction": 1},
    9: {"entry": "Friday close", "exit": "Monday close", "direction": 1},
    10: {"expiry_weekday": "Thursday until 2025-08-28, Tuesday from 2025-09-02", "entry": "open", "exit": "close", "direction": "with previous day"},
}


def _batch1_stories(paths) -> dict:
    out = {}
    for line in paths.batch1_md.read_text().splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|", line)
        if m:
            out[int(m.group(1))] = (m.group(2).strip(), m.group(3).strip())
    return out


def seed_batch1(paths=None, on: date = date(2026, 10, 18)) -> list:
    """Seed the 10 Batch 1 ideas, all REJECTED, with their Task 5 stats (read from results/ideas_batch1_results.json). Counts as 10 trials."""
    p = paths or cfg.PATHS
    if load(p) or tl.read(p):
        raise RegistryError("registry or ledger is not empty: seeding is done once")
    res = json.loads(p.batch1_results.read_text())
    stories = _batch1_stories(p)
    rows = []
    for r in res["results"]:
        n = r["idea"]
        rule = {"kind": "batch1", "idea": n, "module": "forced_trader_ideas", "code_hash": res["code_hash"], "params": RULES1[n]}
        keep = ("n_trades", "mean_net", "mean_gross", "boot_p", "null_p", "first_n", "first_mean", "second_n", "second_mean", "win_rate", "window", "skipped")
        row = {"id": f"B1-{n:02d}", "batch": 1, "name": r["name"], "story": stories[n][0] + ": " + stories[n][1], "rule": rule, "rule_hash": re_.rule_hash(rule),
               "family_hash": re_.family_hash(rule), "cost": 0.001, "created": str(on), "status": "rejected", "variant_of": [], "verdict": r["verdict"],
               "dev_stats": {k: r[k] for k in keep}, "dev_max_drawdown": None, "forward_since": None, "promoted_on": None, "retired_on": None,
               "retire_reason": "failed the Task 5 pass rule (alpha 0.005)"}
        tl.append({"event": "register", "idea_id": row["id"], "batch": 1, "rule_hash": row["rule_hash"], "status": "rejected", "cost": 0.001, "variant_of": [],
                   "source": "Task 5 (research/ideas/results/ideas_batch1_results.json)"}, p, on)
        tl.append({"event": "trial", "idea_id": row["id"], "batch": 1, "rule_hash": row["rule_hash"], "alpha": 0.005, "verdict": r["verdict"],
                   "n_trades": r["n_trades"], "mean_net": r["mean_net"], "boot_p": r["boot_p"], "null_p": r["null_p"],
                   "source": "research/ideas/ledger_ideas.jsonl (IDEAS_BATCH1)"}, p, on)
        rows.append(row)
    _save(rows, p)
    return rows


def md_row(idea_id: str, paths=None) -> str:
    r = get(idea_id, paths)
    return f"| {r['id']} | {r['story']} | `{re_.canon(r['rule'])}` | cost {r['cost']} | hash {r['rule_hash'][:12]} |"


def main(argv=None) -> None:
    a = sys.argv[1:] if argv is None else argv
    cmd = a[0] if a else "list"
    if cmd == "list":
        for r in load():
            print(f"{r['id']}  {r['status']:9s} {r['verdict'] or '-':12s} {r['rule_hash'][:12]}  {r['name']}")
    elif cmd == "show":
        print(json.dumps(get(a[1]), indent=1))
    elif cmd == "check":
        pr = problems()
        print("registry and ledger are consistent" if not pr else "\n".join(pr))
        sys.exit(1 if pr else 0)
    elif cmd == "seed":
        print(f"seeded {len(seed_batch1())} ideas")
    elif cmd == "register":
        spec = json.loads(Path(a[1]).read_text())
        r = register(spec["id"], spec["batch"], spec["name"], spec["story"], spec["rule"], spec.get("cost", cfg.DEFAULT_COST), "--allow-variant" in a)
        print("registered", r["id"], r["rule_hash"][:12], "- now write it into the dated docs/ideas/IDEAS_BATCH md (use: registry.py md-row", r["id"] + ")")
    elif cmd == "md-row":
        print(md_row(a[1]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
