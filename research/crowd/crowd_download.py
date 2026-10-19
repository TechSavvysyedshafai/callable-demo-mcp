"""Download the expired NIFTY weekly option candles (5-minute, WITH open interest) that Task 10 (crowd positioning, B5-01) needs: for each dev expiry from
2024-10-03, calls AND puts at the 11 strikes R-250 .. R+250 (R = S rounded to 50, S = close of the 09:25 bar of the entry day), entry expiry = that week's expiry.
Method and file names as research/wheel/wheel_download.py and research/selling/download_needed.py (contract list per expiry, <expiry>_<strike><CE|PE>.csv in
research/data/expired_options/NIFTY, candle window expiry-9d .. expiry, resumable). Strikes come from the index bar only (known at 09:25), never from option prices.
Throttle: research/upstox/upstox_api.py's own, with its three caps set to about half INSIDE THIS PROCESS (Task 11 shares the per-user limit); the file is not edited.
Token: UPSTOX_ANALYTICS_TOKEN from the environment, never printed or saved. Dev only (expiries to 2026-04-16).
  python research/crowd/crowd_download.py [--dry-run]
Writes research/data/crowd_download_log.csv (one row per missing contract) and crowd_lot_sizes.csv (lot size per expiry from the contract list)."""

import csv
import sys
from datetime import timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "upstox")]
import crowd_core as cc  # noqa: E402
import upstox_api as u  # noqa: E402

KEY = "NSE_INDEX|Nifty 50"
LOG = cc.DATA / "crowd_download_log.csv"
LOTS = cc.DATA / "crowd_lot_sizes.csv"
u.LIMITS = ((1.0, 22), (60.0, 225), (1800.0, 950))  # about half of the standard caps (45 / 450 / 1900), this process only


def needed(plans: list) -> dict:
    """{expiry: [(strike, kind), ...]} for every week that has an S."""
    need: dict = {}
    for p in plans:
        if p["skipped"] is not None:
            continue
        need[p["expiry"]] = [(k, kind) for k in cc.strike_grid(p["spot"]) for kind in ("CE", "PE")]
    return need


def main(dry: bool = False) -> None:
    bars, closes, expiries = cc.wc.load_index()
    plans = cc.make_plans(bars, expiries)
    need = needed(plans)
    total = sum(len(v) for v in need.values())
    print(f"{len(expiries)} expiries; {len(need)} with a signal bar; {total} contracts wanted; "
          f"{len(expiries) - len(need)} weeks without S (no download): {[str(p['expiry']) for p in plans if p['skipped']]}")
    if dry:
        return
    cc.OPT_DIR.mkdir(parents=True, exist_ok=True)
    saved = have = failed = 0
    log = []
    lots = list(csv.DictReader(LOTS.open())) if LOTS.exists() else []  # a resumed run keeps the lot sizes already read
    seen_lots = {r['expiry'] for r in lots}
    for ex in expiries:
        todo = [(k, kind) for k, kind in need.get(ex, []) if not (cc.OPT_DIR / f"{ex.isoformat()}_{k}{kind}.csv").exists()]
        have += len(need.get(ex, [])) - len(todo)
        if not todo:
            continue
        try:
            contracts = u.get("/v2/expired-instruments/option/contract", {"instrument_key": KEY, "expiry_date": ex.isoformat()})["data"]
        except u.UpstoxError as err:
            failed += len(todo)
            print(f"  {ex}: contract list failed: {str(err)[:80]}")
            log += [{"expiry": ex, "strike": k, "kind": kind, "status": "contract_list_failed"} for k, kind in todo]
            continue
        if contracts and ex.isoformat() not in seen_lots:
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
                df.to_csv(cc.OPT_DIR / f"{ex.isoformat()}_{k}{kind}.csv", index=False)
                saved += 1
            else:
                failed += 1
                log.append({"expiry": ex, "strike": k, "kind": kind, "status": "no_candles"})
        print(f"{ex}: done ({saved} saved, {failed} failed so far)", flush=True)
        for path, rows, cols in ((LOG, log, ["expiry", "strike", "kind", "status"]), (LOTS, lots, ["expiry", "lot_size"])):  # rewrite each week: safe to stop
            with path.open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=cols)
                w.writeheader()
                w.writerows(rows)
    print(f"Saved {saved} files; {have} already present; {failed} missing/failed; contracts wanted: {total}")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
