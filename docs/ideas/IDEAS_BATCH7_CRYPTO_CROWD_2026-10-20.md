# Batch 7: "Bet against the crowd" on crypto perpetual futures, using Binance's public retail-positioning data (pre-registered 2026-10-20, BEFORE any test)

Research only. Public archive files, no API key, no account, no orders. Not advice to trade crypto (India: heavy tax and legal limits, noted earlier).

## Data (verified reachable 2026-10-20)
Binance's public historical archive, S3 host `s3-ap-northeast-1.amazonaws.com/data.binance.vision` (the vanity host data.binance.vision is blocked from the container; the S3 host works, no key). The fapi.binance.com API is geo-blocked from US-based servers (HTTP 451), so do NOT use it.
- Positioning: `data/futures/um/daily/metrics/{SYMBOL}/{SYMBOL}-metrics-{YYYY-MM-DD}.zip`, 5-minute rows with columns: create_time, symbol, sum_open_interest, sum_open_interest_value, count_toptrader_long_short_ratio (top traders, by accounts), sum_toptrader_long_short_ratio (top traders, by position size), count_long_short_ratio (ALL accounts, the retail-dominated crowd), sum_taker_long_short_vol_ratio. BTCUSDT files start 2020-09-01 (verified).
- Prices: `data/futures/um/monthly/klines/{SYMBOL}/1d/{SYMBOL}-1d-{YYYY-MM}.zip` (daily candles, open time 00:00 UTC). If a month is missing, use the daily klines path.
- Symbols: BTCUSDT (primary), ETHUSDT (confirmation).
- Dev period: from each symbol's first metrics date to 2025-12-31. HOLDOUT: 2026-01-01 onward. Do not download, open or compute on any file dated 2026-01-01 or later. (Create the dev/holdout split in the fetcher: simply never request post-2025-12-31 files.)

## Rule (fixed; ONE trial: BTCUSDT; trial 17 overall; alpha = 0.05 / 17 = 0.00294)
- Crowd measure: x_D = ln(count_long_short_ratio) from the 5-minute row stamped 23:50:00 UTC on day D (last row fully before the 00:00 trade; skip the day if the row is missing, count skips).
- z_D = (x_D - mean of x over the previous 90 daily values) / their sample std, using only days BEFORE D (minimum 60 prior values; earlier days produce no signal).
- If z_D >= +1.5 (crowd heavily long) go SHORT BTCUSDT perpetual; if z_D <= -1.5 (crowd heavily short) go LONG; else flat.
- Entry at the open of day D+1 (00:00 UTC kline open); exit at the open of day D+2 (24-hour hold). Trades do not overlap (a day D+1 signal can only enter after the prior trade closes; with a 24h hold and a daily cadence consecutive days chain, which is allowed: each signal is its own trade).
- Cost: 0.12% of notional per round trip (taker fee 0.05% per side = 0.10%, plus 0.02% slippage). Funding payments are NOT modelled (state it as an assumption; report the average funding rate over the sample if the archive provides it, information only).
- Pass (all): number of trades >= 100; mean net return per trade > 0; one-sided block bootstrap (blocks of 5 trades, 10,000 resamples) p < 0.00294; positive mean net in each half of the dev period (split at the calendar midpoint); beats a random-entry null (same number of trades, same long/short mix, random days, 10,000 draws) with p < 0.00294; and the SAME rule on ETHUSDT (confirmation, not a trial) has a positive mean net per trade.
- Verdict SURVIVES / REJECT / INCONCLUSIVE (INCONCLUSIVE = BTC mean > 0 and bootstrap p < 0.05 but not the strict bar).
- Information only, NOT trials: threshold 1.0 and 2.0; holds of 4 hours and 3 days; the opposite (follow-the-crowd) direction; the top-trader measure (count_toptrader_long_short_ratio) and the retail minus top-trader spread; per-year results; zero-cost results; the largest single loss and the year-by-year drawdown.
- No variants, no tuning of thresholds or windows after seeing results. Skipped days counted and reported. Do NOT append to research/ideas/loop/ledger_loop.jsonl (the project manager appends the trial after merging); record trial id B7-01 and its numbers in your results JSON.
