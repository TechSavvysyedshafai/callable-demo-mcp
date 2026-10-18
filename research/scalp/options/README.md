# Option scalping (buying ATM calls/puts) - NIFTY first, then BANKNIFTY / FINNIFTY / MIDCPNIFTY / SENSEX

Research + **paper** trading only; no real orders. The signal is still `../strategy.py` (+1 = buy CE, -1 = buy PE);
option exits are `OPTIONS` there (stop / target as % of premium, max hold).

Two evidence levels - do not confuse them:
1. **Model-based backtest** (`evaluate_opt.py`): option prices are Black-Scholes from index bars + India VIX, IV held
   constant intraday. Fast, but the result depends heavily on implied vs realized vol, skew, and the real spread.
   It prints both vols and marks the run INVALID when realized >= implied (that flatters option buyers).
2. **Real quotes** (`live_options.py`): paper-trades at the real ask (buy) / bid (sell) AND records every option
   quote to `data/options_ticks/`. Kite has no expired-contract history, so recording is how you build a real
   dataset. Treat only this as proof.

```bash
python ../../fetch_data.py --interval 5minute --years 3      # NIFTY index bars (from research/)
python fetch_options_data.py                                  # India VIX (non-NIFTY: --underlying BANKNIFTY ...)
python evaluate_opt.py --underlying NIFTY --runs 200          # model-based verdict
python evaluate_opt.py --synthetic-phi 0.5                    # pipeline self-check on fake data
python live_options.py --underlying NIFTY                     # live paper trade + record quotes (market hours)
python ../tests/test_options.py; python ../tests/test_quote_paper.py
```
Underlying settings (lot size, strike step, weekly vs monthly expiry, expiry weekday) are in `contracts.py` and are
FROM MEMORY - verify them. Live code reads real lots/expiries from Kite's instruments dump.
Costs: `costs_opt.py` (verify STT / exchange charges). A round trip on a Rs150 premium needs ~1.2 premium points (~2.4
NIFTY points at delta 0.5; options STT is 0.15% on sell premium since 1 Apr 2026) just to break even - far less than futures in index points, but option buyers also fight theta
and the bid-ask spread, and expiry-day gamma can wipe a position in minutes (`min_dte_days=1` avoids expiry day).

Not yet wired: option mode in `lifecycle.py` (champion/challenger). It uses the same `strategy.py` interface, so it can be added once there is real quote data worth protecting.
