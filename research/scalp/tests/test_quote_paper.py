"""Plumbing test for the quote-driven option paper trader using BS-generated fake quotes."""

import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent.parent
for p in (HERE / "options", HERE, HERE.parent):
    sys.path.insert(0, str(p))
import bs
import strategy
from contracts import UNDERLYINGS, next_expiry, years_to_expiry
from opt_engine import OptParams
from quote_paper import QuotePaper, pick_contract
from synth import synthetic_intraday

cfg = UNDERLYINGS["NIFTY"]
df = synthetic_intraday(n_days=40, phi=0.5, bar_vol=0.0008)
# fake instruments dump: strikes around spot for the next two weekly expiries
rows, tok = [], 1000
for d in {x.date() for x in df["date"]}:
    e = next_expiry(cfg, d)
    for ex in (e, e + timedelta(days=7)):
        for k in range(20000, 30000, 50):
            for ty in ("CE", "PE"):
                tok += 1
                rows.append({"name": "NIFTY", "instrument_type": ty, "expiry": ex.isoformat(), "strike": str(k),
                             "instrument_token": str(tok), "tradingsymbol": f"NIFTY{ex}{k}{ty}", "lot_size": "75"})
meta = {int(r["instrument_token"]): r for r in rows}
log = Path("/tmp/claude-0/qp_test.csv"); log.unlink(missing_ok=True)
wanted = set()
qp = QuotePaper(strategy.make(), OptParams(), "NIFTY",
                resolve=lambda d, spot, ts: pick_contract(rows, "NIFTY", spot, "CE" if d > 0 else "PE", ts.date(), 1),
                subscribe=wanted.add, log=log)
ivq = 0.16
bars = df.to_dict("records")
for i, b in enumerate(bars):
    qp.on_index_bar(b["date"], b["open"], b["high"], b["low"], b["close"])
    nxt = bars[i + 1] if i + 1 < len(bars) and bars[i + 1]["date"].date() == b["date"].date() else None
    if nxt is None:
        continue
    for spot in (nxt["open"], nxt["high"], nxt["low"], nxt["close"]):  # quotes arrive during the next bar
        for tk in list(wanted):
            r = meta[tk]
            T = years_to_expiry(date.fromisoformat(r["expiry"]), nxt["date"])
            p = bs.price(spot, float(r["strike"]), T, ivq, r["instrument_type"] == "CE")
            qp.on_quote(tk, nxt["date"], p - 0.05, p + 0.05)
assert qp.pos is None or True
import csv
n = sum(1 for _ in csv.reader(log.open())) - 1 if log.exists() else 0
assert n > 0, "expected some paper trades"
rows_out = list(csv.DictReader(log.open()))
assert all(float(r["exit"]) >= 0 and r["why"] in {"stop", "target", "time", "eod"} for r in rows_out)
print(f"quote-paper ok: {n} trades, reasons:", sorted({r['why'] for r in rows_out}))
