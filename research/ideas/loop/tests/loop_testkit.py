"""Shared helpers for the loop tests: temporary file locations, synthetic market data with a known built-in edge, a batch declaration file."""

import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

LOOP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LOOP))
import loop_config as cfg  # noqa: E402
import registry as reg  # noqa: E402
import rule_engine as rules  # noqa: E402


def approx(a, b, tol=1e-9):
    assert abs(a - b) <= tol, (a, b)


def tmp_paths(seed_batch1=True):
    """Paths pointing at a fresh temp folder (the real registry/ledger/log are never touched). Returns (paths, TemporaryDirectory)."""
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    p = cfg.Paths(registry=root / "registry.jsonl", ledger=root / "ledger_loop.jsonl", forward_log=root / "forward_log.csv", results=root / "results",
                  dev_dir=root / "dev")
    if seed_batch1:
        reg.seed_batch1(p)
    return p, td


def make_daily(n=1200, start="2018-10-22", edge=0.012, seed=1, vix=False):
    """Random-walk NIFTY-like daily rows. Built-in edge: after any down close-to-close day, the NEXT day's open->close return is `edge` higher.
    Optionally an India VIX series. Returns (daily, vix_or_None)."""
    rng = np.random.default_rng(seed)
    dts = pd.bdate_range(start, periods=n)
    O, C = np.zeros(n), np.zeros(n)
    c_prev, prev_ret = 10000.0, 0.0
    for i in range(n):
        O[i] = c_prev * (1 + rng.normal(0, 0.002))
        r = rng.normal(0, 0.006) + (edge if prev_ret <= 0 and edge else 0.0)
        C[i] = O[i] * (1 + r)
        prev_ret = C[i] / c_prev - 1
        c_prev = C[i]
    d = pd.DataFrame({"date": dts, "open": O, "close": C})
    v = None
    if vix:
        v = pd.DataFrame({"date": dts, "close": 15 * np.exp(np.cumsum(rng.normal(0, 0.06, n)))})
    return d, v


def make_5min(days=40, start="2024-01-01", seed=2):
    rng = np.random.default_rng(seed)
    rows, px = [], 20000.0
    for day in pd.bdate_range(start, periods=days):
        t = day + pd.Timedelta(hours=9, minutes=15)
        for _ in range(75):  # 09:15 .. 15:25
            o = px
            px = o * (1 + rng.normal(0, 0.0007))
            rows.append((t, o, px))
            t += pd.Timedelta(minutes=5)
    return pd.DataFrame(rows, columns=["date", "open", "close"])


STRONG = {"kind": "daily", "conditions": [{"feature": "ret_1d", "op": "<=", "value": 0.0}], "direction": {"fixed": 1},
          "entry": {"day": 1, "px": "open"}, "exit": {"day": 1, "px": "close"}}
NOISE = {"kind": "daily", "conditions": [{"feature": "weekday", "op": "==", "value": 2}], "direction": {"fixed": -1},
         "entry": {"day": 0, "px": "close"}, "exit": {"day": 1, "px": "close"}}
GAP = {"kind": "daily", "conditions": [{"feature": "gap_next", "op": "abs_gt", "value": 0.007}], "direction": {"against": "gap_next"},
       "entry": {"day": 1, "px": "open"}, "exit": {"day": 1, "px": "close"}}


def register_batch(p, batch, rules_by_name, on=date(2026, 10, 25), cost=0.001):
    """Register ideas B<batch>-01.. and write the dated declaration md next to the temp registry. Returns the md path."""
    for k, (name, rule) in enumerate(rules_by_name.items(), 1):
        reg.register(f"B{batch}-{k:02d}", batch, name, f"story for {name}", rule, cost, True, p, on)
    return write_md(p, batch, on)


def write_md(p, batch, on):
    rows = reg.batch_of(batch, p)
    md = p.registry.parent / f"IDEAS_BATCH{batch}_{on}.md"
    md.write_text(f"# Batch {batch} declared {on} BEFORE testing\n\n" + "\n".join(reg.md_row(r["id"], p) for r in rows) + "\n")
    return md
