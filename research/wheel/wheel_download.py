"""Download the expired NIFTY weekly option candles Task 8 (wheel) needs: only the PUT and the CALL per week (no wings), 5-minute candles.
Same method and file names as research/selling/download_needed.py (contract list per expiry, strikes from the entry-bar close, <expiry>_<strike><CE|PE>.csv,
candle window expiry-9d .. expiry, resumable) but for the wheel's two short legs, over every entry spot any run can use (see wheel_core.needed_contracts).
Throttling is done by research/upstox/upstox_api.py. Token comes from UPSTOX_ANALYTICS_TOKEN and is never printed or saved. Dev only (expiries to 2026-04-16).
Writes research/data/wheel_download_log.csv (one row per missing contract) and wheel_lot_sizes.csv (lot size per expiry from the contract list)."""

import csv
import sys
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "upstox")]
import upstox_api as u  # noqa: E402
import wheel_core as wc  # noqa: E402

KEY = "NSE_INDEX|Nifty 50"
LOG = wc.DATA / "wheel_download_log.csv"
LOTS = wc.DATA / "wheel_lot_sizes.csv"


def main() -> None:
    bars, closes, expiries = wc.load_index()
    need = wc.needed_contracts(bars, expiries)
    wc.OPT_DIR.mkdir(parents=True, exist_ok=True)
    by_exp: dict = {}
    for ex, k, kind in sorted(need):
        by_exp.setdefault(ex, []).append((k, kind))
    saved = have = failed = 0
    log, lots = [], []
    for ex in expiries:
        todo = [(k, kind) for k, kind in by_exp.get(ex, []) if not (wc.OPT_DIR / f"{ex.isoformat()}_{k}{kind}.csv").exists()]
        have += len(by_exp.get(ex, [])) - len(todo)
        if not todo:
            continue
        try:
            contracts = u.get("/v2/expired-instruments/option/contract", {"instrument_key": KEY, "expiry_date": ex.isoformat()})["data"]
        except u.UpstoxError as err:
            failed += len(todo)
            print(f"  {ex}: contract list failed: {str(err)[:80]}")
            log += [{"expiry": ex, "strike": k, "kind": kind, "status": "contract_list_failed"} for k, kind in todo]
            continue
        if contracts:
            lots.append({"expiry": ex, "lot_size": contracts[0].get("lot_size", "")})
        cmap = {(int(float(c["strike_price"])), c["instrument_type"]): c for c in contracts}
        for k, kind in todo:
            c = cmap.get((k, kind))
            if c is None:
                failed += 1
                log.append({"expiry": ex, "strike": k, "kind": kind, "status": "not_in_expired_list"})
                continue
            try:
                df = u.expired_candles(c["instrument_key"], "5minute", ex - timedelta(days=9), ex)
            except u.UpstoxError as err:
                failed += 1
                log.append({"expiry": ex, "strike": k, "kind": kind, "status": f"failed: {str(err)[:60]}"})
                continue
            if len(df):
                df.to_csv(wc.OPT_DIR / f"{ex.isoformat()}_{k}{kind}.csv", index=False)
                saved += 1
            else:
                failed += 1
                log.append({"expiry": ex, "strike": k, "kind": kind, "status": "no_candles"})
        print(f"{ex}: done ({saved} saved, {failed} failed so far)")
    for path, rows, cols in ((LOG, log, ["expiry", "strike", "kind", "status"]), (LOTS, lots, ["expiry", "lot_size"])):
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
    print(f"Saved {saved} files; {have} already present; {failed} missing/failed; contracts wanted: {len(need)}")


if __name__ == "__main__":
    main()
