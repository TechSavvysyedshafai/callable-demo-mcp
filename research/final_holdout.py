"""ONE-SHOT test of the final candidate on the locked holdout. Humans run this, not the agent."""

import argparse
import json
from pathlib import Path

import harness as h
import kite_data as kd
from candidate import predict

LOCK = kd.HOLDOUT_DIR / "holdout_used.lock"
p = argparse.ArgumentParser()
p.add_argument("--interval", default="day")
p.add_argument("--confirm", action="store_true", help="I understand this can only be run once")
a = p.parse_args()

if LOCK.exists():
    raise SystemExit(f"Holdout already spent ({LOCK.read_text().strip()}). Collect fresh data to test again.")
if not a.confirm:
    raise SystemExit("Pass --confirm. The holdout is scored exactly once.")

dev, hold = kd.load_dev(a.interval), kd.load_holdout(a.interval)
# Holdout bars need history for the lookback: prepend the tail of dev, score only holdout targets.
full = __import__("pandas").concat([dev.tail(h.MIN_TRAIN + 5), hold], ignore_index=True)
res = h.evaluate(full, predict, trials=1)  # single pre-registered candidate -> no trial penalty here
LOCK.write_text(f"candidate {h.code_hash(Path(__file__).with_name('candidate.py'))}")
print(json.dumps(res, indent=2))
