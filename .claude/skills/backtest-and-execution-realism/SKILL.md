---
name: backtest-and-execution-realism
description: Use when building or running a backtest, cost model, paper-trading run or promotion decision. Covers fills, costs, slippage sweeps, model-versus-real prices, skipped-signal accounting, risk limits and the paper-trading gate. Never places orders.
---

# Backtest and execution realism

## Fill rules (already implemented; keep them)
Decide at a bar's close; fill at the NEXT bar's open plus slippage. If a bar touches both stop and target, the stop is assumed first. Flat by 15:15. Daily loss cap, trade cap, and a `KILL` file.
A signal you could not price (no contract, no candle) is a skipped signal: **count and report it**; they are usually the large-move days.

## Costs (verified against Upstox's published charges on 2026-10-18; re-verify before relying)
Futures: brokerage Rs20 or 0.05%; STT 0.05% sell (from 1 Apr 2026); NSE transaction 0.00183%; stamp 0.002% buy; GST 18% on brokerage+exchange.
Options (buying): brokerage Rs20 flat (Rs30 on Plus); STT 0.15% of sell premium (from 1 Apr 2026); NSE transaction 0.03553% of premium; stamp 0.003% buy; GST 18%.
Files: `research/scalp/costs.py`, `research/scalp/options/costs_opt.py`. STT, exchange and stamp are the same at every broker; brokerage differs.

## Prices: model vs real
- Black-Scholes prices with constant IV are a **plumbing tool, not evidence**. The model-priced option "pass" disappeared on real candles. Never present model-based results as findings.
- Real candles have no bid/ask: treat `slippage_rs` as an assumption and **sweep it (0.10 / 0.20 / 0.30)**. An edge must survive the middle value.
- The only true spread data is `live_options.py` quote recordings. Prefer them for any claim about execution.
- Use the real expiry calendar and the real lot size for the period; weekly-expiry weekday and lot size changed. Avoid expiry day (`min_dte_days=1`) unless that is the hypothesis.

## Paper trading and promotion
- Paper trade on real quotes (`live_options.py`, `live_feed.py`) with champion/challenger (`research/scalp/lifecycle.py`). One challenger at a time, frozen before it sees live data, judged only on later sessions.
- Eligibility numbers live in `lifecycle.py`. **Promotion needs the owner's explicit `--approve`.**
- There is **no order placement code** in this repo. Do not add any. Real money requires the owner's written approval after the full gate, plus broker rules (registered static IP; algo registration above 10 orders/second; no market orders).

## Risk basics to state in every report
Position size in rupees and lots; worst day in the sample; max drawdown; trades per day; what happens on expiry day or a gap through the stop.
