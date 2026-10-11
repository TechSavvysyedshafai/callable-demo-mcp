"""End-to-end: champion + challenger paper-trade the same fake bars; scoreboard; gated promotion."""

import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
tmp = tempfile.mkdtemp()
os.environ["SCALP_STATE"] = tmp
import lifecycle as lc  # noqa: E402
from paper import Fleet  # noqa: E402
from synth import synthetic_intraday  # noqa: E402

strat = HERE / "strategy.py"
backup = strat.read_text()
try:
    lc.ensure_champion(lc.load_registry())                      # baseline champion = default strategy
    strat.write_text(backup.replace("z_entry=1.5", "z_entry=1.0"))  # a variant becomes the challenger
    lc.freeze("2023-12-31", check_eval=False)
    try:
        lc.freeze("2023-12-31", check_eval=False); raise AssertionError("2nd challenger must be refused")
    except SystemExit:
        pass
    fleet = Fleet()
    assert len(fleet.traders) == 2
    for r in synthetic_intraday(n_days=70, phi=0.5, seed=3).itertuples():
        fleet.on_bar(r.date, r.open, r.high, r.low, r.close)
    fleet.end_session()
    sb = lc.scoreboard()
    print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in sb.items()})
    msg = lc.promote(approve=False) if sb["status"].startswith("ELIGIBLE") else "not eligible: " + sb["status"]
    print(msg)
    if sb["status"].startswith("ELIGIBLE"):
        assert "Re-run with --approve" in msg
        assert lc.load_registry()["challenger"] is not None      # nothing changed without approval
        print(lc.promote(approve=True)); assert lc.load_registry()["challenger"] is None
    else:
        print(lc.reject())
finally:
    strat.write_text(backup)
    shutil.rmtree(tmp, ignore_errors=True)
print("lifecycle ok")
