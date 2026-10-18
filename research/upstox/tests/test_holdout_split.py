import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from holdout_split import dev_expiries, split_vix

cut = pd.Timestamp("2026-04-16")
v = pd.DataFrame({"date": pd.to_datetime(["2026-04-15", "2026-04-16", "2026-04-17", "2026-09-01"]), "close": [1, 2, 3, 4]})
dev, hold = split_vix(v, cut)
assert list(dev["close"]) == [1, 2] and list(hold["close"]) == [3, 4]
assert dev_expiries(["2026-05-05", "2026-04-14", "2026-04-21", "2026-04-07"], cut) == ["2026-04-07", "2026-04-14", "2026-04-21"]
print("holdout split ok")
