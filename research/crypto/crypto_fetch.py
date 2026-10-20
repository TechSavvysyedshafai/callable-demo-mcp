"""Task 12 (B7-01, crowd positioning on crypto perpetuals): download the Binance public-archive files the pre-registered study needs.
Doc: docs/ideas/IDEAS_BATCH7_CRYPTO_CROWD_2026-10-20.md. Public files over plain HTTPS: no API key, no account, no login, no orders.
Host: the S3 endpoint s3-ap-northeast-1.amazonaws.com/data.binance.vision (the vanity host is blocked from the container).

HOLDOUT RULE (enforced here, in the fetcher): a file whose date is later than 2025-12-31 is NEVER requested. The directory listing returns names only;
names dated 2026-01-01 or later are discarded unread and are not even counted. Monthly kline files after 2025-12 are never requested.
Polite rate (about 3 requests per second), resumable (saved files are skipped), retries with backoff.
  python research/crypto/crypto_fetch.py            (writes research/data/crypto/{raw,parsed}/..., git-ignored, and fetch_log.json)"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import quote

import requests

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data" / "crypto"
HOST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
LAST_DEV_DATE = "2025-12-31"  # inclusive; HOLDOUT = 2026-01-01 onward
LAST_DEV_MONTH = "2025-12"
SYMBOLS = tuple(os.environ.get("CRYPTO_SYMBOLS", "BTCUSDT,ETHUSDT").split(","))  # a second process may take one symbol
PAUSE = 0.35  # seconds between requests (about 3 per second)
UA = {"User-Agent": "Mozilla/5.0 (research data fetch; public archive)"}
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\.zip$")
MONTH_RE = re.compile(r"(\d{4}-\d{2})\.zip$")


def _get(url: str, params: dict | None = None, tries: int = 6) -> requests.Response:
    for k in range(tries):
        try:
            time.sleep(PAUSE)
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code in (200, 404):
                return r
        except requests.RequestException:
            pass
        time.sleep(2 ** k)
    raise RuntimeError(f"giving up on {url}")


def list_keys(prefix: str) -> list:
    """All object keys under a prefix (S3 listing, paginated with `marker`)."""
    keys, marker = [], ""
    while True:
        r = _get(HOST + "/", {"delimiter": "/", "prefix": prefix, "marker": marker})
        r.raise_for_status()
        found = re.findall(r"<Key>([^<]+\.zip)</Key>", r.text)
        keys += found
        if "<IsTruncated>true</IsTruncated>" not in r.text or not found:
            return keys
        marker = found[-1]


def allowed(key: str) -> bool:
    """True only for dev files: a day <= 2025-12-31, or a month <= 2025-12."""
    m = DATE_RE.search(key)
    if m:
        return m.group(1) <= LAST_DEV_DATE
    m = MONTH_RE.search(key)
    return bool(m) and m.group(1) <= LAST_DEV_MONTH


def fetch(key: str, kind: str, sym: str, log: dict) -> None:
    assert allowed(key), key  # belt and braces: never request a holdout file
    name = key.rsplit("/", 1)[1]
    raw, par = DATA / "raw" / kind / sym / name, DATA / "parsed" / kind / sym / name.replace(".zip", ".csv")
    if par.exists():
        log["have"] += 1
        return
    r = _get(HOST + "/" + quote(key))
    if r.status_code != 200:
        log["missing"].append(name)
        return
    raw.parent.mkdir(parents=True, exist_ok=True)
    par.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(r.content)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        names = z.namelist()
        assert len(names) == 1, (name, names)
        par.write_bytes(z.read(names[0]))
    log["saved"] += 1


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    out = {"host": HOST, "last_dev_date": LAST_DEV_DATE, "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "symbols": {}}
    for sym in SYMBOLS:
        for kind, prefix in (("metrics", f"data/futures/um/daily/metrics/{sym}/"), ("klines1d", f"data/futures/um/monthly/klines/{sym}/1d/"),
                             ("klines1d_daily", f"data/futures/um/daily/klines/{sym}/1d/")):
            keys = [k for k in list_keys(prefix) if allowed(k)]  # post-2025 names are dropped here, unread
            if os.environ.get("CRYPTO_REVERSE"):
                keys = keys[::-1]  # a second worker walks the list from the other end
            log = {"listed_dev_files": len(keys), "saved": 0, "have": 0, "missing": []}
            if kind == "klines1d_daily":
                continue  # daily klines are only a fallback for a missing month; decided after the monthly pass
            for i, k in enumerate(keys):
                fetch(k, kind, sym, log)
                if (i + 1) % 200 == 0:
                    print(sym, kind, i + 1, "/", len(keys), flush=True)
            out["symbols"].setdefault(sym, {})[kind] = {**log, "first": min(keys).rsplit("/", 1)[1] if keys else None, "last": max(keys).rsplit("/", 1)[1] if keys else None}
            print(sym, kind, {k: (v if not isinstance(v, list) else len(v)) for k, v in log.items()}, flush=True)
    (DATA / ("fetch_log_" + "_".join(SYMBOLS) + ("_rev" if os.environ.get("CRYPTO_REVERSE") else "") + ".json")).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
