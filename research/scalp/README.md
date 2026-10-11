# Scalping research + paper trading (NIFTY futures, Kite data)

Research and **paper** trading only. No code here places real orders, on purpose.

```bash
cd research
python fetch_data.py --interval 5minute --years 3   # Kite data (needs Connect subscription + daily token)
cd scalp
python evaluate.py                    # backtest strategy.py on dev data, with costs, vs random entries
python evaluate.py --synthetic-phi 0.5   # dry run on fake data with a planted edge (pipeline self-check)
python paper.py --replay              # paper-trade demo on fake bars
python live_feed.py                   # LIVE paper trading from Kite ticks (untested; market hours)
python final_holdout.py --confirm     # human, once, at the end
```

How it avoids fooling you
- **Costs first.** `costs.py` models brokerage, STT, exchange, SEBI, stamp, GST and slippage. `evaluate.py` prints
  the break-even points a trade must move just to pay fees (about 8 index points per round trip with the defaults).
  **Verify every rate in `costs.py` (lot size, STT) before trusting results.**
- **Same engine for backtest and paper trading** (`engine.py`): decide at bar close, fill at next open + slippage,
  stop before target if a bar touches both, forced flat by 15:15, daily loss limit, trade cap, `KILL` file.
- **Random-entry control.** The strategy must beat random entries run under identical exits and costs.
- **Trial penalty + hidden holdout** as in the daily harness: every distinct `strategy.py` version tightens the bar.
- **Self-check (synthetic):** with no edge it fails (costs eat it); with a strong planted edge it passes.

Limits: bar-level simulation (no order book, no queue position, no partial fills); live feed untested;
intraday data availability depends on your Kite plan. Passing here is necessary, not sufficient: paper trade for weeks first.
