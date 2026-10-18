"""Independent re-computation of SELL1 (V1 and V2, slippage Rs0.20) with plain loops and the csv module: no code shared with
backtest.py (costs formula re-derived by hand). Prints total net and the largest per-week difference against results/selling_results.json."""

import csv
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "data"
SLIP, Q = 0.20, 75


def side(prem, is_buy):
    t = prem * Q
    exch, sebi = 0.0003553 * t, 0.000001 * t
    return 20 + exch + sebi + 0.18 * (20 + exch + sebi) + (0.00003 * t if is_buy else 0.0015 * t)


bars = [(datetime.fromisoformat(r["date"]), float(r["close"])) for r in csv.DictReader(open(D / "nifty_5minute_dev.csv"))]
daily = {r["date"][:10]: float(r["close"]) for r in csv.DictReader(open(D / "nifty_day_dev.csv"))}
days = sorted({b[0].date() for b in bars})
expiries = [datetime.fromisoformat(r["expiry"]).date() for r in csv.DictReader(open(D / "nifty_expiries.csv"))]
expiries = [e for e in expiries if datetime(2024, 10, 3).date() <= e <= datetime(2026, 4, 16).date()]


def candles(e, strike, kind):
    p = D / "expired_options" / "NIFTY" / f"{e}_{strike}{kind}.csv"
    if not p.exists():
        return None
    out = {}
    for r in csv.DictReader(open(p)):
        out[datetime.fromisoformat(r["date"])] = (float(r["open"]), float(r["close"]))
    return out


res = {}
for var in ("V1", "V2"):
    nets = {}
    for e in expiries:
        target = e - timedelta(days=7)
        ed = max(d for d in days if d <= target)
        i = next(k for k, b in enumerate(bars) if b[0].date() == ed and b[0].hour * 60 + b[0].minute >= 570)
        ts, spot = bars[i]
        sc = math.ceil(round(spot * 1.012 / 50, 9)) * 50
        sp = math.floor(round(spot * 0.988 / 50, 9)) * 50
        legs = {"sc": (sc, "CE"), "lc": (sc + 150, "CE"), "sp": (sp, "PE"), "lp": (sp - 150, "PE")}
        data = {n: candles(e, k, c) for n, (k, c) in legs.items()}
        if any(v is None or ts not in v for v in data.values()):
            continue
        fill = {n: max(v[ts][0] + (SLIP if n in ("lc", "lp") else -SLIP), 0) for n, v in data.items()}
        credit = fill["sc"] + fill["sp"] - fill["lc"] - fill["lp"]
        cost = sum(side(fill[n], n in ("lc", "lp")) for n in fill)
        stop_at = None
        if var == "V2":
            grid = [b[0] for b in bars if b[0] >= ts and b[0].date() <= e]
            last = {}
            for gi, t in enumerate(grid):
                for n, v in data.items():
                    if t in v:
                        last[n] = v[t][1]
                cost_now = last["sc"] + last["sp"] - last["lc"] - last["lp"]
                if cost_now - credit >= 2 * credit:
                    stop_at = gi
                    break
        if stop_at is not None:
            exit_px = {}
            for n, v in data.items():
                nxt = grid[stop_at + 1] if stop_at + 1 < len(grid) else None
                last_close = max((t for t in v if t <= grid[stop_at]))  # last known candle at or before the trigger bar
                px = v[nxt][0] if nxt in v else v[last_close][1]
                exit_px[n] = max(px + SLIP, 0) if n in ("sc", "sp") else max(px - SLIP, 0)
            gross = credit - (exit_px["sc"] + exit_px["sp"] - exit_px["lc"] - exit_px["lp"])
            cost += sum(side(exit_px[n], n in ("sc", "sp")) for n in exit_px)
        else:
            s = daily[e.isoformat()]
            iv = lambda k, c: max(s - k, 0) if c == "CE" else max(k - s, 0)  # noqa: E731
            owed = iv(*legs["sc"]) - iv(*legs["lc"]) + iv(*legs["sp"]) - iv(*legs["lp"])
            gross = credit - owed
            cost += 0.0015 * Q * sum(iv(*legs[n]) for n in legs)
        nets[e.isoformat()] = gross * Q - cost
    res[var] = nets

main = json.load(open(Path(__file__).parent / "results" / "selling_results.json"))
for var in ("V1", "V2"):
    mine = {w["expiry"]: w["net_rs"] for w in main[var]["weeks_0.20"] if w["skipped"] is None}
    diff = max(abs(mine[k] - res[var][k]) for k in mine) if mine.keys() == res[var].keys() else float("nan")
    print(var, "weeks", len(res[var]), "total net Rs", round(sum(res[var].values()), 2), "main total", round(sum(mine.values()), 2),
          "same weeks:", mine.keys() == res[var].keys(), "max abs weekly difference Rs", diff)
