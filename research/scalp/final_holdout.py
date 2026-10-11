"""ONE-SHOT: score the final strategy on the locked holdout (outside the repo). Humans run this."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import kite_data as kd
from evaluate import evaluate

LOCK = kd.HOLDOUT_DIR / "scalp_holdout_used.lock"
a = argparse.ArgumentParser()
a.add_argument("--interval", default="5minute")
a.add_argument("--runs", type=int, default=200)
a.add_argument("--confirm", action="store_true")
a = a.parse_args()
if LOCK.exists():
    raise SystemExit(f"Holdout already spent: {LOCK.read_text().strip()}")
if not a.confirm:
    raise SystemExit("Pass --confirm. The holdout is scored exactly once.")
res = evaluate(kd.load_holdout(a.interval), trials=1, runs=a.runs)
LOCK.write_text("used")
print(json.dumps(res, indent=2, default=str))
