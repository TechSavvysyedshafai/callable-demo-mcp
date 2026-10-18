# Batch 4: the "wheel" strategy on NIFTY (pre-registered 2026-10-18, BEFORE any test)

## What the wheel is
Sell a cash-secured put. If it is "assigned", you own the shares at the strike. Then sell a covered call against the shares. If the call is "called away", you are back to cash and sell a put again. Repeat. Income = option premium. Cost = you keep the downside of owning the shares and give up the upside above the call strike.

## Scope limits (honest)
- The real wheel is done on single stocks (physical settlement). We have NO stock option history. NIFTY index options are CASH-settled (no shares change hands), so this is an INDEX PROXY: assignment = the index settles below the put strike; we then treat it as holding a NIFTY futures-equivalent long bought AT the strike (equivalently: pay the put's intrinsic loss in cash, and hold long exposure from the strike price afterwards). Called away = the index settles above the call strike; we sell the exposure at the strike.
- Data: real expired NIFTY weekly option candles (Upstox, 5-minute) 2024-10-03 to dev cutoff 2026-04-16 (about 80 weeks), the same file layout Task 3 used (research/selling). Holdout (after 2026-04-16) NOT touched. 80 weeks cannot show crash risk and have low power.

## Rules (fixed; one trial)
- Weekly cycle, same entry rule as research/selling: entry at the first 5-minute bar at or after 09:30 on the trading day nearest on or before (expiry - 7 calendar days); sale fills at that bar's open minus slippage.
- State CASH: sell the put at strike = spot x 0.988 rounded DOWN to a multiple of 50 (spot = close of the entry bar, as in selling). Hold to expiry; settlement = official daily close of the expiry day. If settle < strike: assigned: long exposure from the strike; the cash loss is (strike - settle) x lot, i.e. mark the exposure at the settle price. If settle >= strike: premium kept, stay CASH.
- State LONG (exposure carried from a previous assignment, marked at the settle of the prior expiry): sell the call at strike = spot x 1.012 rounded UP to a multiple of 50, same entry rule. The long exposure continues to be marked weekly at official closes. If settle > strike: called away: exposure sold at the strike (gain capped), back to CASH. Else stay LONG.
- Lot = 75 units (as in Tasks 3 to 7; real lot size changed, unverified). Capital base for return: 1 lot notional at the first entry spot (so "return" = total net P&L / that notional). Cash earns 0 in the wheel and in the benchmark (shown separately with 6.5% on idle cash for information).
- Costs: research/scalp/options/costs_opt.py (frozen) for every option fill and settlement STT on in-the-money legs (as in research/selling); the share/exposure leg costs: futures round trip 0.065% of notional per assignment and per called-away event (exchange, STT 0.05% on sells, brokerage Rs 20 per order); no slippage on the exposure leg beyond that. Slippage on options Rs 0.10 / 0.20 / 0.30 per fill (0.20 primary).
- Benchmark: buy 1 lot-equivalent NIFTY exposure at the first entry spot and hold to the last expiry, same costs on entry and exit.

## Primary test (the pass rule)
Weekly series D_t = wheel net P&L in week t minus benchmark net P&L in week t (Rs per lot, both marked weekly at the official closes). One-sided block bootstrap (blocks of 5 weeks, 10,000 resamples) for mean(D) > 0.
Pass: mean(D) > 0 at slippage 0.20 AND p < 0.05 / 14 = 0.00357 (this is trial 14 overall) AND max drawdown of the wheel is smaller than that of the benchmark AND the result holds in both halves of the sample (split at the calendar midpoint).
Also report (information only, not a pass criterion): total return, per-week mean and median, worst week, max drawdown, Sharpe-like ratio (mean/std of weekly P&L), time spent in CASH vs LONG, number of assignments and call-aways, premium collected vs paid out (like the condor study).

## Controls (reported, not trials)
(1) Short-put-only (never sell calls, never hold after assignment: stay CASH and just pay the intrinsic): does the call overlay help? (2) Covered-call-only on the benchmark exposure (always LONG, sell calls every week). (3) Entry shifted by +1 and +2 bars.

Stop rules: any week missing a needed contract is skipped and counted; report the count. Report negatives as plainly as positives. Append the single trial to the loop ledger (research/ideas/loop/trial_ledger.py, append only) so the global counter becomes 14. Survivors, if any, go to forward paper only.
