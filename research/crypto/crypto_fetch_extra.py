"""Task 12, information-only extras (NOT trials): monthly 1-hour klines (needed only for the 4-hour-hold check) and monthly funding-rate files (needed only to
report the average funding rate; funding is NOT modelled in the rule). Same holdout rule and etiquette as crypto_fetch.py: months after 2025-12 are never requested.
  python research/crypto/crypto_fetch_extra.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crypto_fetch as cf  # noqa: E402


def main() -> None:
    out = {}
    for sym in cf.SYMBOLS:
        for kind, prefix in (("klines1h", f"data/futures/um/monthly/klines/{sym}/1h/"), ("funding", f"data/futures/um/monthly/fundingRate/{sym}/")):
            keys = [k for k in cf.list_keys(prefix) if cf.allowed(k)]
            log = {"listed_dev_files": len(keys), "saved": 0, "have": 0, "missing": []}
            for k in keys:
                cf.fetch(k, kind, sym, log)
            out.setdefault(sym, {})[kind] = {**log, "first": keys[0].rsplit("/", 1)[1] if keys else None, "last": keys[-1].rsplit("/", 1)[1] if keys else None}
            print(sym, kind, {a: (b if not isinstance(b, list) else len(b)) for a, b in log.items()}, flush=True)
    (cf.DATA / "fetch_log_extra.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
