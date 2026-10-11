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

## Continuous improvement (champion / challenger, human-approved)
```
During market hours   python scalp/live_feed.py       # champion (+ challenger) paper-trade the same live bars
After the close       python scalp/lifecycle.py scoreboard
Research (only when no challenger is under test; weekly is plenty)
                      agent edits scalp/strategy.py -> python scalp/evaluate.py --runs 200  (needs PASS)
                      python scalp/lifecycle.py freeze --tuned-through <last session date used for tuning>
Decision              python scalp/lifecycle.py promote --approve    # only when scoreboard says ELIGIBLE
                      python scalp/lifecycle.py reject               # or discard the challenger
```
- A challenger is judged **only on sessions after** `--tuned-through`, so it is never graded on data it was tuned on.
- Eligibility: >= 20 forward days, >= 100 forward trades, positive net P&L after costs, and a paired block-bootstrap
  win over the champion (5% lower bound > 0). Not eligible after 60 days = reject. Thresholds are constants in `lifecycle.py`.
- One challenger at a time keeps the number of trials (and the luck) down. Nothing changes code during a session.
- Optional automation: a nightly cron can run `claude -p "<follow research/program.md>"` for the research step; keep the
  `promote --approve` step manual.
- State lives in `scalp/state/` (git-ignored): registry, frozen strategy snapshots, per-version paper logs.
- Self-test: `python scalp/tests/test_lifecycle.py` (real edge -> eligible; no edge -> rejected).
