"""Download exactly the four expired-option contracts each SELL1 week needs (same file names as download_expired_options.py).

Why: `download_expired_options.py --strikes 10` centres strikes on the close BEFORE expiry, but the condor is built from the spot
7 days earlier, so 76 of 81 weeks were missing a leg (a coverage problem, found from skip counts only, before any P&L was looked at).
Strikes here come from the NIFTY 5-minute bar at the entry bar (information available at entry), never from later prices.
Dev only (expiries up to 2026-04-16). Resumable: existing files are skipped. Token via UPSTOX_ANALYTICS_TOKEN (never printed).
"""

import sys
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "upstox")]
import backtest as bt  # noqa: E402
import upstox_api as u  # noqa: E402

KEY = "NSE_INDEX|Nifty 50"

if __name__ == "__main__":
    bars, closes, expiries = bt.load_index()
    days = sorted(set(bars["date"].dt.date))
    bt.OPT_DIR.mkdir(parents=True, exist_ok=True)
    saved = failed = have = 0
    for ex in expiries:
        d = bt.entry_day(ex, days)
        e = bt.entry_bar(bars, d) if d else None
        if e is None:
            print(f"{ex}: no entry bar")
            continue
        need = {n: (s, k) for n, (s, k) in bt.leg_strikes(float(bars.loc[e, "close"])).items()}
        todo = [(n, s, k) for n, (s, k) in need.items() if not (bt.OPT_DIR / f"{ex.isoformat()}_{s}{k}.csv").exists()]
        have += len(need) - len(todo)
        if not todo:
            continue
        try:
            contracts = u.get("/v2/expired-instruments/option/contract", {"instrument_key": KEY, "expiry_date": ex.isoformat()})["data"]
        except u.UpstoxError as err:
            failed += len(todo)
            print(f"  {ex}: contract list failed: {err}")
            continue
        by = {(int(float(c["strike_price"])), c["instrument_type"]): c for c in contracts}
        for n, s, k in todo:
            c = by.get((s, k))
            if c is None:
                failed += 1
                print(f"  {ex}: no contract {s}{k} in the expired list")
                continue
            try:
                df = u.expired_candles(c["instrument_key"], "5minute", ex - timedelta(days=9), ex)
            except u.UpstoxError as err:
                failed += 1
                print(f"  {ex}: {s}{k} failed: {err}")
                continue
            if len(df):
                df.to_csv(bt.OPT_DIR / f"{ex.isoformat()}_{s}{k}.csv", index=False)
                saved += 1
            else:
                failed += 1
                print(f"  {ex}: {s}{k} returned no candles")
        print(f"{ex}: done ({saved} saved, {failed} failed so far)")
    print(f"Saved {saved} files; {have} already present; {failed} failed")
