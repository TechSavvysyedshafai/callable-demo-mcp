# Batch 3: "Settlement mechanics" (pre-registered 2026-10-18, BEFORE any test)

Source: Business Standard, 16 Oct 2026, "CAS review: Sebi announces last 30-minute VWAP method for settlement" (one news article; the SEBI circular itself is NOT read: verify before trusting any detail).
What the article says (verified from the article only):
- Index derivatives settle on the VWAP of the constituent stocks over the last 30 minutes of the continuous session (3:00-3:30 pm). The article calls this "retaining the earlier method".
- From 7 Dec 2026: closing auction (CAS) becomes a separate 3:30-3:40 pm session; expiring index contracts stop trading at 3:30 pm. Order-carry-forward changes (iceberg orders) start 8 Feb 2027.
- The current CAS regime (since 3 Aug 2026) drew complaints about settlement-price spikes and thin liquidity.

## Why a rule like this can create a pattern (the logic)
On expiry day the option payoff is not decided by the last trade. It is decided by an AVERAGE of the last 30 minutes. An average of a random walk moves less than its endpoint: for a window of length T the standard deviation of the average around its starting value is about 0.58 (= 1/sqrt(3)) of the standard deviation of the endpoint. So at 3:00 pm an at-the-money expiring option behaves like an "Asian" option with about 58% of the volatility a normal option would have. If the market keeps pricing these last-30-minute options as if the settlement were the last print, they are too expensive, and selling them could earn the difference. If market makers already price the averaging, there is nothing to earn. Costs and thin expiry-day liquidity may eat any small edge.

## Scope limits (honest)
- The CAS regime (3 Aug 2026 onward) lies inside the hidden holdout period (dev cutoff 2026-04-16). It is OFF LIMITS to research. These tests use dev data (settlement was by the same 30-minute method before CAS, per the article's "retaining"). The new rules only matter if they change that method; the article says they do not for index derivatives.
- Expiry days: about 80 in dev (real calendar: Thursday until 2025-08-28, Tuesday from 2025-09-02; research/upstox expiry file). Few trades, low power. A pass here means "candidate for forward paper", never "proven".
- Underlying: NIFTY index and real expired NIFTY option candles (Upstox, 5-minute, with open interest).

## Gate G0 (a check, not a trial)
On every dev expiry day compute: A = official daily close (settlement proxy), S0 = open of the 15:00 bar, S1 = close of the 15:25 bar (last print).
Report std(A - S0) / std(S1 - S0). Theory says about 0.58 if the official close is a 30-minute average; about 1.0 if it is the last print. STOP the batch if the ratio is above 0.85 (premise false) and report that.

## Trials (exactly 3; global alpha = 0.05 / 13 total trials ever = 0.00385)
T1 Short straddle into the average. Expiry day, sell the ATM call and put (strike = S0 rounded to nearest 50) at the open of the 15:00 bar; hold to settlement (intrinsic value vs official close). Slippage Rs 0.20 per leg (0.10 and 0.30 reported), costs from research/scalp/options/costs_opt.py, settlement STT on in-the-money legs as in research/selling. Lot 75. Pass: mean net per trade > 0 at 0.20 AND bootstrap p < 0.00385 AND n >= 60 AND both halves positive. Also report: straddle price at 15:00 divided by the model value of an Asian-style straddle (0.58 x sigma x sqrt(T), sigma from the day's earlier 5-minute returns, known at 15:00) as a calibration ratio.
T2 Defined-risk version. As T1 but buy the 100-point-out wings (call +100, put -100) at the same time. Same pass rule.
T3 Pin test (no trading). At 14:55 find the strike with the largest total open interest (call + put) among strikes the files hold. Compare |A - that strike| with |A - K| where K is a random strike drawn uniformly from the same strikes (10,000 draws per day, same strike set). One-sided test that the max-OI strike is closer to the settlement than a random strike. Pass: p < 0.00385.

No variants, no tuning, no extra trials. Report negatives as plainly as positives. Holdout never read. Survivors (if any) go to forward paper only, to be logged from the next expiry.
