"""Download the expired NIFTY option candles Task 7 needs, EXPIRY DAY ONLY (5-minute candles incl. open interest).
Per dev expiry (2024-10-03 .. 2026-04-16): strikes K0 +/- 500 in steps of 50 (K0 = open of the 15:00 NIFTY bar on expiry day, rounded to 50),
CE and PE. That covers the ATM straddle, the +/-100 wings (T1/T2) and the OI scan (T3).
Same file names as research/selling/download_needed.py (<expiry>_<strike><CE|PE>.csv), so files already there are reused (resumable).
Writes research/data/settlement_download_log.csv (one row per expiry: what was listed, saved, missing) and settlement_lot_sizes.csv.
Throttling is done by research/upstox/upstox_api.py. Token comes from UPSTOX_ANALYTICS_TOKEN and is never printed or saved. Dev only."""

import csv
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "upstox")]
import settlement_core as sc  # noqa: E402
import upstox_api as u  # noqa: E402

KEY = "NSE_INDEX|Nifty 50"
LOG = sc.DATA / "settlement_download_log.csv"
LOTS = sc.DATA / "settlement_lot_sizes.csv"


def main() -> None:
    bars, closes, expiries = sc.load_index()
    sc.OPT_DIR.mkdir(parents=True, exist_ok=True)
    log, lots = [], []
    for ex in expiries:
        f = sc.day_frame(bars, ex)
        pair = sc.s0_s1(f)
        if pair is None:
            log.append({"expiry": ex, "status": "no_index_bars", "wanted": 0, "have": 0, "saved": 0, "missing": 0, "lot_size": ""})
            print(f"{ex}: no 15:00/15:25 index bar")
            continue
        k0 = sc.round_strike(pair[0])
        need = [(k, kind) for k in sc.scan_strikes(k0) for kind in ("CE", "PE")]
        todo = [(k, kind) for k, kind in need if not (sc.OPT_DIR / f"{ex.isoformat()}_{k}{kind}.csv").exists()]
        saved = missing = 0
        lot = ""
        status = "ok"
        if todo or True:
            try:
                contracts = u.get("/v2/expired-instruments/option/contract", {"instrument_key": KEY, "expiry_date": ex.isoformat()})["data"]
            except u.UpstoxError as err:
                contracts = []
                status = f"contract_list_failed: {str(err)[:80]}"
            if contracts:
                lot = contracts[0].get("lot_size", "")
            by = {(int(float(c["strike_price"])), c["instrument_type"]): c for c in contracts}
            for k, kind in todo:
                c = by.get((k, kind))
                if c is None:
                    missing += 1
                    continue
                try:
                    df = u.expired_candles(c["instrument_key"], "5minute", ex, ex)
                except u.UpstoxError as err:
                    missing += 1
                    status = f"candle_error: {str(err)[:60]}"
                    continue
                if len(df):
                    df.to_csv(sc.OPT_DIR / f"{ex.isoformat()}_{k}{kind}.csv", index=False)
                    saved += 1
                else:
                    missing += 1
        have = len(need) - len(todo) + saved
        if not contracts and status == "ok":
            status = "empty_contract_list"
        log.append({"expiry": ex, "status": status, "wanted": len(need), "have": have, "saved": saved, "missing": missing, "lot_size": lot})
        lots.append({"expiry": ex, "lot_size": lot})
        print(f"{ex}: wanted {len(need)} have {have} (new {saved}, missing {missing}) lot {lot} {status}")
    with LOG.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(log[0]))
        w.writeheader()
        w.writerows(log)
    with LOTS.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["expiry", "lot_size"])
        w.writeheader()
        w.writerows(lots)
    print(f"log: {LOG}")


if __name__ == "__main__":
    main()
