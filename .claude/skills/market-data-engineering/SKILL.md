---
name: market-data-engineering
description: Use when downloading, validating, storing or joining market data (index bars, India VIX, expired option candles, live option quotes) from Upstox or Kite. Covers rate limits, token handling, data quality checks and holdout separation.
---

# Market data engineering

## Sources and how to call them
- **Upstox (preferred, free data):** `research/upstox/`. Token = environment variable `UPSTOX_ANALYTICS_TOKEN` (never print or write it). Run `check_setup.py` first.
  Always send a normal `User-Agent` (Cloudflare error 1010 blocks Python's default). Limits: 50/second, 500/minute, **2,000 per 30 minutes**; `upstox_api.py` throttles for you.
  Minute candles: from Jan 2022, 1 month per request. Daily: from 2000, 10 years per request. Expired option candles need the Plus plan; the expiry list reached back to Oct 2024.
- **Kite:** `research/kite_data.py` and the Worker in `src/`. Needs a paid Connect plan and a daily token; no expired-contract history.
- **Live recording:** `research/scalp/options/live_options.py` saves option quotes (bid/ask, OI) to `research/data/options_ticks/` because candles have no spread.

## File layout and separation
- Dev data: `research/data/` (git-ignored). **Holdout: `~/.nifty_holdout/` (outside the repo, never read by research).** `kite_data.write_split` enforces the split.
- Expired option files: `research/data/expired_options/NIFTY/<expiry>_<strike><CE|PE>.csv`; expiry calendar: `research/data/nifty_expiries.csv`.

## Quality checks to run on every dataset (build/extend `research/qa/data_quality.py`)
1. Timezone: timestamps are IST, naive after conversion; sessions 09:15-15:30; 5-minute bars = 75 per full day; list days that are short (half-days) or missing.
2. Duplicates, sorted order, NaN, zero or negative prices, high < low, open/close outside high/low.
3. Outliers: bar moves > 5 standard deviations; verify against the daily bar before trusting or dropping. Never silently delete.
4. **Regime changes that corrupt history:** NIFTY lot size changed over time; weekly expiry weekday changed; tax rates changed (STT rose on 1 Apr 2026). Use the real expiry calendar, not a formula, and note which period each rule covers.
5. Option files: strikes covered per expiry vs where spot actually traded (missing strikes bias results; report the skipped share), volume/OI gaps, candles missing for illiquid bars.
6. Reproducibility: record download date, source endpoint, and row counts in `research/RESULTS.md`.

## Hygiene
Handle 429/timeouts with backoff; make downloaders resumable (skip saved files); never loop forever; log failures and re-run until `0 failed`.
