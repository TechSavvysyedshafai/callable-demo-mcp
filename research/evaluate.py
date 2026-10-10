"""Run the candidate through the walk-forward dev evaluation and log the trial."""

import argparse
import json
from pathlib import Path

import harness as h
import kite_data as kd
from candidate import predict

p = argparse.ArgumentParser()
p.add_argument("--interval", default="day")
p.add_argument("--step", type=int, default=1, help="origin stride (raise for faster runs)")
a = p.parse_args()

df = kd.load_dev(a.interval)
chash = h.code_hash(Path(__file__).with_name("candidate.py"))
seen = h.seen_hashes()
trials = len(seen | {chash})  # distinct candidate versions tried, including this one
res = h.evaluate(df, predict, trials, a.step)
h.log_trial(chash, {"verdict": res["verdict"], "rel_improvement": res["rel_improvement"],
                    "mae": res["mae"]["candidate"]})
print(json.dumps(res, indent=2))
