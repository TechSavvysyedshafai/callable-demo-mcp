"""Champion / challenger lifecycle. Rules that keep 'continuous optimisation' honest:
  * ONE challenger at a time, frozen (snapshotted) before it ever sees live data.
  * It must have PASSED evaluate.py on dev data to be frozen.
  * Both strategies paper-trade the same live bars; the challenger is judged ONLY on sessions after it was frozen.
  * Promotion needs enough forward days/trades, positive net P&L, and a paired win over the champion, AND a
    human typing --approve. Nothing here edits code during a session or places real orders.

  python lifecycle.py status | scoreboard | freeze --tuned-through YYYY-MM-DD | promote [--approve] | reject
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
STATE = Path(os.environ.get("SCALP_STATE", HERE / "state"))
REG, VERS, LOGS = STATE / "registry.json", STATE / "versions", STATE / "logs"
LEDGER = HERE / "ledger.jsonl"
MIN_FORWARD_DAYS, MIN_FORWARD_TRADES, MAX_FORWARD_DAYS, ALPHA = 20, 100, 60, 0.05


def file_hash(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(f"strat_{Path(path).stem}", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_registry() -> dict:
    return json.loads(REG.read_text()) if REG.exists() else {"champion": None, "challenger": None, "history": []}


def save_registry(r: dict):
    STATE.mkdir(parents=True, exist_ok=True)
    REG.write_text(json.dumps(r, indent=2, default=str))


def snapshot(src: Path) -> dict:
    VERS.mkdir(parents=True, exist_ok=True)
    h = file_hash(src)
    dest = VERS / f"{h}.py"
    shutil.copy(src, dest)
    return {"hash": h, "file": str(dest)}


def ensure_champion(reg: dict) -> dict:
    if reg["champion"] is None:  # first run: the working strategy.py becomes the baseline champion
        reg["champion"] = {**snapshot(HERE / "strategy.py"), "since": str(date.today())}
        save_registry(reg)
    return reg


def active_strategies() -> list[tuple[str, object]]:
    """[(name, module)] that the paper trader should run: champion and, if any, challenger."""
    reg = ensure_champion(load_registry())
    out = [(reg["champion"]["hash"], load_module(reg["champion"]["file"]))]
    if reg["challenger"]:
        out.append((reg["challenger"]["hash"], load_module(reg["challenger"]["file"])))
    return out


def freeze(tuned_through: str, check_eval: bool = True) -> dict:
    reg = ensure_champion(load_registry())
    if reg["challenger"]:
        raise SystemExit("A challenger is already under test. Promote or reject it first (one at a time limits trials).")
    h = file_hash(HERE / "strategy.py")
    if h == reg["champion"]["hash"]:
        raise SystemExit("strategy.py is identical to the champion; nothing to test.")
    if check_eval:
        last = [json.loads(l) for l in LEDGER.read_text().splitlines() if l] if LEDGER.exists() else []
        if not any(e["hash"] == h and e["verdict"] == "PASS" for e in last):
            raise SystemExit("This strategy.py has no PASS in the evaluate.py ledger. Run evaluate.py on real dev data first.")
    reg["challenger"] = {**snapshot(HERE / "strategy.py"), "frozen_after": tuned_through, "frozen_on": str(date.today())}
    save_registry(reg)
    return reg["challenger"]


def _daily(name: str) -> pd.Series:
    p = LOGS / f"{name}_daily.csv"
    if not p.exists():
        return pd.Series(dtype=float)
    d = pd.read_csv(p)
    return d.groupby("day")["pnl_rs"].sum()


def _trades(name: str) -> int:
    p = LOGS / f"{name}_daily.csv"
    return int(pd.read_csv(p)["n_trades"].sum()) if p.exists() else 0


def scoreboard(seed: int = 0) -> dict:
    reg = load_registry()
    if not reg["champion"] or not reg["challenger"]:
        return {"status": "no challenger under test"}
    ch, cp = reg["challenger"], reg["champion"]
    a, b = _daily(ch["hash"]), _daily(cp["hash"])
    days = sorted(d for d in set(a.index) & set(b.index) if d > ch["frozen_after"])
    if not days:
        return {"status": "KEEP TESTING", "forward_days": 0}
    a, b = a.loc[days], b.loc[days]
    d = (a - b).to_numpy()
    rng, n, blk = np.random.default_rng(seed), len(d), 3
    starts = rng.integers(0, max(n - blk + 1, 1), size=(10000, -(-n // blk)))
    idx = (starts[:, :, None] + np.arange(blk)).reshape(10000, -1)[:, :n] % n
    lower = float(np.quantile(d[idx].mean(axis=1), ALPHA))
    trades = int(pd.read_csv(LOGS / f"{ch['hash']}_daily.csv").query("day > @ch['frozen_after']")["n_trades"].sum())
    res = {"forward_days": n, "challenger_trades": trades, "challenger_net_rs": float(a.sum()),
           "champion_net_rs": float(b.sum()), "mean_daily_edge_rs": float(d.mean()), "edge_ci_lower_rs": lower}
    enough = n >= MIN_FORWARD_DAYS and trades >= MIN_FORWARD_TRADES
    if enough and res["challenger_net_rs"] > 0 and lower > 0:
        res["status"] = "ELIGIBLE - run: lifecycle.py promote --approve (human decision)"
    elif n >= MAX_FORWARD_DAYS:
        res["status"] = "REJECT - did not earn promotion within the window"
    else:
        res["status"] = "KEEP TESTING"
    return res


def promote(approve: bool) -> str:
    reg = load_registry()
    sb = scoreboard()
    if not sb["status"].startswith("ELIGIBLE"):
        raise SystemExit(f"Not eligible: {sb}")
    if not approve:
        return f"Would promote {reg['challenger']['hash']} over {reg['champion']['hash']}. Re-run with --approve."
    reg["history"].append({"retired": reg["champion"], "promoted": reg["challenger"], "on": str(date.today()), "scoreboard": sb})
    reg["champion"] = {**reg["challenger"], "since": str(date.today())}
    reg["challenger"] = None
    save_registry(reg)
    return f"Promoted {reg['champion']['hash']}."


def reject() -> str:
    reg = load_registry()
    if reg["challenger"]:
        reg["history"].append({"rejected": reg["challenger"], "on": str(date.today())})
        reg["challenger"] = None
        save_registry(reg)
    return "Challenger cleared."


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("cmd", choices=["status", "scoreboard", "freeze", "promote", "reject"])
    a.add_argument("--tuned-through", help="last session date (YYYY-MM-DD) the challenger was tuned on")
    a.add_argument("--approve", action="store_true")
    a.add_argument("--skip-eval-check", action="store_true", help="testing only")
    a = a.parse_args()
    if a.cmd == "status":
        print(json.dumps(ensure_champion(load_registry()), indent=2, default=str))
    elif a.cmd == "scoreboard":
        print(json.dumps(scoreboard(), indent=2))
    elif a.cmd == "freeze":
        if not a.tuned_through:
            sys.exit("--tuned-through is required: forward testing counts only sessions AFTER this date.")
        print(json.dumps(freeze(a.tuned_through, not a.skip_eval_check), indent=2))
    elif a.cmd == "promote":
        print(promote(a.approve))
    else:
        print(reject())
