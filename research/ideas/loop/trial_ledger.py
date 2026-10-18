"""Append-only, hash-chained ledger of everything the loop does that counts: registrations, batch starts, trials, status changes.
Each line carries the hash of the line before it, so editing or deleting an old line is detected by verify().
The global trial counter is just the number of "trial" lines. Alpha for a batch = 0.05 / (all trials ever, including the new batch)."""

from __future__ import annotations

import hashlib
import json
from datetime import date

import loop_config as cfg

GENESIS = "0" * 64


class LedgerTampered(Exception):
    pass


def _canon(o) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def _digest(prev: str, body: dict) -> str:
    return hashlib.sha256((prev + _canon(body)).encode()).hexdigest()


def read(paths=None) -> list:
    p = (paths or cfg.PATHS).ledger
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def verify(paths=None) -> int:
    """Raise LedgerTampered if any line was edited, removed or reordered. Returns the number of lines."""
    prev, n = GENESIS, 0
    for i, ev in enumerate(read(paths)):
        body = {k: v for k, v in ev.items() if k not in ("prev", "hash")}
        if ev.get("prev") != prev or ev.get("seq") != i or ev.get("hash") != _digest(prev, body):
            raise LedgerTampered(f"ledger line {i} does not match its hash chain (edited or removed?)")
        prev, n = ev["hash"], n + 1
    return n


def append(event: dict, paths=None, on: date | None = None) -> dict:
    """Append one event. Never rewrites old lines."""
    p = (paths or cfg.PATHS).ledger
    old = read(paths)
    verify(paths)
    prev = old[-1]["hash"] if old else GENESIS
    body = dict(event)
    body.setdefault("date", str(on or date.today()))
    body["seq"] = len(old)
    ev = dict(body, prev=prev, hash=_digest(prev, body))
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(ev, sort_keys=True, default=str) + "\n")
    return ev


def events(kind: str, paths=None) -> list:
    return [e for e in read(paths) if e["event"] == kind]


def total_trials(paths=None) -> int:
    return len(events("trial", paths))


def trial_for(idea_id: str, paths=None):
    for e in events("trial", paths):
        if e["idea_id"] == idea_id:
            return e
    return None


def batch_alpha(prior_trials: int, n_new: int) -> float:
    """0.05 / (trials already counted + trials in the new batch)."""
    if n_new < 1:
        raise ValueError("a batch needs at least one idea")
    return cfg.FAMILY_ALPHA / (prior_trials + n_new)


def next_batch_alpha(n_new: int = cfg.MAX_BATCH, paths=None) -> float:
    return batch_alpha(total_trials(paths), n_new)
