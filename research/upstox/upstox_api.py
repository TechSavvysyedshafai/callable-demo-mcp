"""Tiny Upstox REST client (standard library only). Reads the token from the UPSTOX_ANALYTICS_TOKEN
environment variable; the token is never printed or written anywhere."""

from __future__ import annotations

import collections
import json
import os
import socket
import ssl
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


# Upstox limits (per user): 50/second, 500/minute, 2000 per 30 minutes. Stay just under all three.
LIMITS = ((1.0, 45), (60.0, 450), (1800.0, 1900))
_sent: collections.deque = collections.deque()


def _throttle(now=time.monotonic, sleep=time.sleep, limits=None) -> None:
    limits = limits or LIMITS
    while True:
        t = now()
        while _sent and t - _sent[0] > limits[-1][0]:
            _sent.popleft()
        wait = 0.0
        for window, cap in limits:
            recent = [x for x in _sent if t - x <= window]
            if len(recent) >= cap:
                wait = max(wait, recent[0] + window - t + 0.01)
        if wait <= 0:
            _sent.append(t)
            return
        sleep(wait)


def get(path: str, params: dict | None = None, retries: int = 6) -> dict:
    url = BASE + path + (("?" + urllib.parse.urlencode(params)) if params else "")
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Authorization": f"Bearer {_token()}",
                                          "User-Agent": "Mozilla/5.0 (compatible; upstox-research/1.0)"})
    for attempt in range(retries):
        _throttle()
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(min(15 * 2**attempt, 300))  # 429 means wait; back off up to 5 minutes
                continue
            raise UpstoxError(e.code, raw) from None
        except (urllib.error.URLError, ssl.SSLError, socket.timeout, ConnectionError, TimeoutError) as e:
            if attempt < retries - 1:  # network blips (e.g. SSL handshake timeout): retry
                time.sleep(min(5 * 2**attempt, 120))
                continue
            raise UpstoxError(0, f"network error: {e}") from None
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
