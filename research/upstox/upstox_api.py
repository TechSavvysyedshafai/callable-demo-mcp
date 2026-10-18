"""Tiny Upstox REST client (standard library only). Reads the token from the UPSTOX_ANALYTICS_TOKEN
environment variable; the token is never printed or written anywhere."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

import pandas as pd

BASE = "https://api.upstox.com"
NIFTY = "NSE_INDEX|Nifty 50"
INDIA_VIX = "NSE_INDEX|India VIX"
IST = "Asia/Kolkata"


class UpstoxError(Exception):
    def __init__(self, code: int, body: str):
        super().__init__(f"HTTP {code}: {body[:300]}")
        self.code, self.body = code, body

    @property
    def needs_plus(self) -> bool:
        return "UDAPI1149" in self.body


def _token() -> str:
    t = os.environ.get("UPSTOX_ANALYTICS_TOKEN", "").strip()
    if not t:
        raise SystemExit("UPSTOX_ANALYTICS_TOKEN is not set - see README.md, step 3.")
    return t


def get(path: str, params: dict | None = None, retries: int = 4) -> dict:
    url = BASE + path + (("?" + urllib.parse.urlencode(params)) if params else "")
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Authorization": f"Bearer {_token()}"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = json.load(r)
            time.sleep(0.05)  # limit is 50 requests/second; stay far below it
            return body
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            if e.code == 429 and attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            raise UpstoxError(e.code, raw) from None
    raise UpstoxError(429, "rate limited")


def key_in_path(key: str) -> str:
    return urllib.parse.quote(key, safe="")


def candles_to_df(rows: list) -> pd.DataFrame:
    cols = ["date", "open", "high", "low", "close", "volume", "oi"]
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=cols[: len(rows[0])])
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert(IST).dt.tz_localize(None)
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def _spans(start: date, end: date, days: int):
    cur = start
    while cur <= end:
        stop = min(cur + timedelta(days=days - 1), end)
        yield cur, stop
        cur = stop + timedelta(days=1)


def historical(key: str, unit: str, interval: int, start: date, end: date) -> pd.DataFrame:
    """Candles for an ACTIVE instrument. Minute data: Upstox allows 1 month per request (intervals 1-15),
    available from Jan 2022. Daily data: 1 decade per request."""
    span = 28 if unit == "minutes" else 3000
    frames = []
    for a, b in _spans(start, end, span):
        path = f"/v3/historical-candle/{key_in_path(key)}/{unit}/{interval}/{b.isoformat()}/{a.isoformat()}"
        frames.append(candles_to_df(get(path)["data"]["candles"]))
    frames = [f for f in frames if len(f)]
    return pd.concat(frames).drop_duplicates("date").sort_values("date").reset_index(drop=True) if frames else candles_to_df([])


def expired_candles(expired_key: str, interval: str, start: date, end: date) -> pd.DataFrame:
    """Candles for an EXPIRED contract (needs Upstox Plus). interval: 1minute|3minute|5minute|15minute|30minute|day."""
    path = f"/v2/expired-instruments/historical-candle/{key_in_path(expired_key)}/{interval}/{end.isoformat()}/{start.isoformat()}"
    return candles_to_df(get(path)["data"]["candles"])
