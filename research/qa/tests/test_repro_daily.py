"""repro_daily_mae.py must agree with a slow, obviously-correct loop on random data (so the 'independent' numbers can be trusted)."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
import repro_daily_mae as rp

rng = np.random.default_rng(3)
r = np.abs(rng.normal(0.011, 0.004, 700))
f = rp.forecasts(r)
assert len(f["origins"]) == 700 - 1 - rp.MIN_TRAIN and f["origins"][0] == rp.MIN_TRAIN and f["origins"][-1] == 698
for k, i in enumerate(f["origins"]):
    h = r[: i + 1]  # only data up to the origin
    w = 0.94 ** np.arange(120)[::-1]
    assert abs(f["candidate"][k] - (0.4 * h[-1] + 0.3 * h[-5:].mean() + 0.3 * h[-22:].mean())) < 1e-12
    assert abs(f["random_walk"][k] - h[-1]) < 1e-12 and abs(f["mean20"][k] - h[-20:].mean()) < 1e-12
    assert abs(f["ewma94"][k] - (w * h[-120:]).sum() / w.sum()) < 1e-12
    assert f["y"][k] == r[i + 1]  # target = the next day
d = np.arange(200, dtype=float)
lo = rp.block_bootstrap_lower(d, 0.05)
assert 80 < lo < 100  # lower 5% bound of a mean around 99.5 must sit below the mean and above half of it
assert rp.block_bootstrap_lower(np.zeros(100), 0.05) == 0.0
print("repro daily ok")
