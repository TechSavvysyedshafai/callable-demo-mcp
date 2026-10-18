# Gold wheel on MCX: feasibility (Task 9a), 2026-10-18

No backtest, no returns, no parameters chosen from prices. Dev data only. The hidden holdout was not read. No order code.
Probe calls: about 60 to the Upstox API (search, expiries, contract lists, candles), well under the throttle.
Probe output is in `research/goldwheel/feasibility/` (no token saved).

## 1. Verdict (answer first)

**NOT FEASIBLE as a backtest on the data we can get today.**

- Upstox's expired-instrument APIs return **nothing for MCX**. Their own docs say: "Expiries is currently not available for the MCX."
  Real calls confirmed it (empty lists for expiries, expired option contracts and expired futures contracts).
- The only gold option candles we can pull are for contracts that are **still listed**. The oldest 5-minute option candle is **2026-09-28**.
  That is 5 months after the dev cut-off (2026-04-16). **Cycles in dev data: 0.**
- Even with perfect data, gold options here are **monthly, not weekly**. One cycle a month means about 12 a year.
  The NIFTY wheel had about 80 weekly cycles and was already called low power. A monthly gold wheel could not pass a corrected p < 0.0036 test in any realistic span.

What is possible instead (needs your decision, see section 6): record live gold option quotes from now (about 12 cycles a year, forward paper only), or look for a different historical source (not verified).

## 2. Which MCX gold contracts exist, and which have options

Source: Upstox instrument search API, queried 2026-10-18 (`/v2/instruments/search`, exchange MCX). **Verified.**

| Contract | Futures lot | Price quote | Rs per Re 1 move | Futures expiry | Options? |
|---|---|---|---|---|---|
| Gold (1 kg) | 1 (= 1 kg) | per 10 g | 100 (qty multiplier 100) | 5th of Dec, Feb, Apr, Jun, Aug, Oct (bi-monthly) | **Yes** |
| Gold Mini (100 g) `GOLDM` | 100 g | per 10 g | 10 (qty multiplier 10) | 5th of every month (listed: Nov 26 to Apr 27) | **Yes** |
| Gold Guinea `GOLDGUINEA` | 8 g | | | last day of every month | **No** (0 option contracts of any type) |
| Gold Petal `GOLDPETAL` | 1 g | | | last day of every month | **No** |
| Gold Ten `GOLDTEN` (10 g) | 10 g | | | last day of every month | **No** |

Futures tick size is Rs 1 per 10 g (Upstox lists tick 100 in paise). A second source (Zerodha Varsity, "Gold part 1") also says Gold Mini is Rs 10 per Re 1 tick.
Guinea, Petal and Ten are tiny futures lots but have no options, so they cannot host a wheel.

**Smallest lot with options: Gold Mini (`GOLDM`), 100 g.** For scale only: one lot is about Rs 14.6 lakh of gold at the Oct 2026 futures level (146,425 per 10 g on 2026-10-16). A cash-secured put would need margin in that range, so this is not a small-capital product.

## 3. Gold Mini options: the facts

| Item | Value | Status |
|---|---|---|
| Underlying | A **futures** contract. Oct 2026 options sit on the Nov 2026 GOLDM future (`MCX_FO\|571445`), Nov options on the Dec future, Dec options on the Jan 2027 future | verified (Upstox `underlying_key`) |
| Lot | 100 g (one lot, price per 10 g, so Rs 10 per Re 1 of premium) | verified (Upstox `lot_size` 100, `qty_multiplier` 10) |
| Style | European. Exercise only at expiry | verified (MCX options page: "only European style commodity options are available"; Dhan page agrees) |
| Strike interval | **Rs 500 on every strike** (140 of 140 gaps in the Oct series, 120 of 120 in Nov, 111 of 111 in Dec). 112 to 141 strikes per series (about Rs 119,500 to 189,500 in the Oct series) | verified for today's listing only. Not read from an MCX circular. MCX can change it; the Scribd title "Strike Price Interval ... Gold and Gold Mini Options" suggests it has been revised before |
| Option tick | Rs 0.50 (Upstox `tick_size` 50 paise) | verified (Upstox) |
| Weekly options | **None.** One expiry a month (Upstox `weekly` field empty; only 3 expiries listed: 2026-10-29, 2026-11-27, 2026-12-29) | verified for today's listing |
| Expiry day | Listed expiries: Thu 2026-10-29, Fri 2026-11-27, Tue 2026-12-29. About 5 business days **before** the futures expiry on the 5th | verified (Upstox). **Conflict:** Dhan's option chain shows 28 Oct 2026 and 28 Dec 2026, one day earlier than Upstox's 29 Oct and 29 Dec. Not resolved. Could be a settlement-day versus last-trading-day labelling difference. The MCX rule quoted in the Gold leaflet snippet is "3 business days prior to the first business day of the Tender Period"; I could not read the Gold Mini leaflet itself (MCX pages load by script) |
| Listing window | A series appears only about 4 weeks before expiry. The 29 Oct series' oldest candle is 2026-09-28; the 29 Dec series' oldest is 2026-10-06 | verified (candle probe) |
| Exercise settles into futures | **Yes.** MCX: options "on exercise, devolve into the underlying futures contracts. All such devolved futures positions open at the strike price of exercised options." | verified (mcxindia.com/options, read 2026-10-18) |
| ITM / OTM rule | Contracts launched from 1 Feb 2022: all ITM options exercise automatically unless the long holder says no; OTM expire worthless. At-the-money (settlement equal to strike) counts as OTM and expires worthless | verified (MCX FAQ "Changes in options exercise mechanism", citing SEBI circular SEBI/HO/CDMRD/DNP/CIR/P/2022/01 of 3 Jan 2022) |
| Final settlement price | MCX "Due Date Rate" of the underlying future on the option expiry day | verified (same FAQ); how the rate is computed for GOLDM: not read |

### Physical delivery risk (the important part for a "wheel")
- A short put or call that finishes in the money becomes a **futures position** (short put: long future at the strike; short call: short future at the strike). It is not cash-settled like NIFTY.
- That futures position then sits on a contract that expires about 5 business days later (the 5th of the next month). Gold futures at MCX are **physically delivered** if held to expiry. Zerodha Varsity says delivery is compulsory and advises closing at least 4 days before expiry; Zerodha's help reply says they close positions before expiry because they do not support delivery. **Not verified from an MCX circular:** exact tender-period start dates for GOLDM and the exact delivery-period margin rules. Pre-expiry and delivery-period margin text I found was on the **NSE** commodity page, not MCX, so I am **not** using it.
- So the "LONG" state in a gold wheel is never a quiet buy-and-hold. It is a futures position that must be closed or rolled within about 4 trading days after assignment. This changes the economics from the NIFTY proxy (cost of one futures round trip at each assignment, plus the roll).

## 4. Data availability: Upstox probe (the real result)

All calls done 2026-10-18 with the Plus plan token (never printed or saved).

| Probe | Result |
|---|---|
| `/v2/expired-instruments/expiries` with the active GOLDM Nov future key, and with the Gold Dec future key | `data: []` (empty). Keys like `MCX_COM\|117` and `MCX_FO\|GOLDM` are rejected as invalid |
| `/v2/expired-instruments/option/contract` for both underlyings at a past date (2026-09-28) | `data: []` |
| `/v2/expired-instruments/future/contract` for the GOLDM key, 2026-10-05 | `data: []` |
| Expired-candle call using an `<active key>\|29-10-2026` style expired key | `candles: []` |
| Upstox docs (`get-expiries`) | "Expiries is currently not available for the MCX." Docs say up to about 6 months of expiries for other markets |
| Instrument search for already-expired GOLDM contracts | Search returns only listed contracts; expired ones are absent, so I cannot even find old keys to try |
| `/v3/historical-candle` for **active** GOLDM options | **Works.** 5-minute and daily candles with open interest (OI) in the 7th field. GOLDM 146500 CE 29 Oct: 14 daily rows from 2026-09-28, 2,434 five-minute rows from 2026-09-28 09:10 to 2026-10-16 23:25 (MCX trades to 23:30 or 23:55) |
| Active futures history | GOLDM Nov 2026 future: daily from 2026-05-06 (117 rows). Gold Dec 2026 future: daily from 2025-12-16 (174 rows). Both have OI. Expired futures: not retrievable |

Answers to your questions:
- **Does Upstox return MCX gold option candles with OI?** Yes, for listed contracts, 5-minute and daily, with OI.
- **How far back?** Only to the day a currently listed series started (about 4 weeks before its expiry). Earliest option candle seen: 2026-09-28.
- **Earliest expiry / number of expiries / strikes?** Earliest option expiry available: 2026-10-29 (not yet expired). Expiries: 3 (Oct, Nov, Dec 2026). Strikes: 141 / 121 / 112. **Expired expiries: 0.**
- **Number of cycles in dev data (to 2026-04-16): 0.**

Files: `feasibility/expiries_probe.json`, `expired_api_probe_log.json`, `history_depth_probe.json`, `active_gold_option_contracts.csv` (listed GOLD and GOLDM option contracts, 2026-10-18).

Incidental exposure: the probe printed a few candle rows, so I did see current gold price levels (futures near 146,000 per 10 g) and some option premiums. I did not compute anything from them and the draft below uses percentages, not price levels.

## 5. Costs (Upstox, commodity options and futures)

Status key: V = read on a live page today, A = assumed or single-source.

| Item | Rate | Status |
|---|---|---|
| Upstox brokerage, MCX options | Flat Rs 20 per executed order | A. A third-party summary says so (investorgain.com); the Upstox charges page I fetched showed a mixed table without a clear commodity row, so I could not read the commodity row. The repo already uses Rs 20 per order |
| Upstox brokerage, MCX futures | Rs 20 per executed order or 0.03% whichever is lower (Zerodha's rule; Upstox's commodity-futures row not read) | A |
| Exchange transaction charge, MCX options | **0.0418% of premium** | V on Zerodha's charges page (read 2026-10-18). MCX's own circular not read. Upstox's rate may differ |
| Exchange transaction charge, MCX futures | 0.0021% of turnover | V on Zerodha's page, same caveat |
| CTT (commodity transaction tax), futures | 0.01% on the sell side, non-agricultural (gold qualifies) | V on Zerodha's page; matches a government-linked explainer (ies.gov.in) |
| CTT, options | **0.05% on the sell side, on the premium** | V on Zerodha's page. **Open:** a post-Budget-2026 note on LinkedIn says equity STT rose on 1 Apr 2026 (futures 0.05%, options 0.15%); its CTT bullet was cut off and the page could not be fetched. Zerodha, read today, still shows commodity CTT unchanged. I did not read the Finance Act. Whether CTT applies to the **intrinsic value of options exercised at expiry** (like equity STT does) is **not verified**. For a gold wheel that matters |
| Stamp duty | 0.003% on the buy side for options, 0.002% on the buy side for futures | V on Zerodha's page; Upstox's own equity-segment table shows the same 0.003% / 0.002% |
| GST | 18% on (brokerage + SEBI fee + exchange charges) | V on Zerodha's page |
| SEBI turnover fee | Rs 10 per crore | V on Zerodha's page |
| Margin and delivery rules near expiry (MCX) | Not verified (see section 3) | not verified |

## 6. Recommendation and DRAFT rule set (for the owner to pre-register, only if you want a forward-paper test)

Because there is no historical data, a backtest cannot be pre-registered. What remains:

1. **Do not test the gold wheel as a backtest.** State this in the ledger of ideas as "blocked by data".
2. **If you want to pursue it:** start recording live GOLDM option quotes (bid, ask, OI) and the GOLDM future from now, using the existing live-recording pattern in `research/scalp/options/live_options.py`. After about 3 years you would have about 36 monthly cycles. That is still low power. Treat any forward result as a paper-trading observation only, not a gate pass.
3. **Or check a different history source** (not verified by me): the MCX website has "Bhav Copy" and "Reports on Historical Data" pages with end-of-day option prices and OI, and some vendors sell it. If you can get daily option settlement prices back to the launch of GOLDM options (I have not verified the launch date; a Scribd document title mentions "Gold Mini (100 Grams) Options ... January 2024 Contract Onwards", which suggests early 2024), the maximum is about 28 monthly cycles to April 2026. That is too few for a corrected test of p < 0.05/14. Daily data also cannot reproduce the 5-minute entry rule.

### DRAFT rules (illustrative; every number is a proposal to be fixed by you before any data is seen)
- **Instrument:** MCX Gold Mini (`GOLDM`) options on futures, 1 lot = 100 g. Underlying for marking: the GOLDM future the option sits on.
- **Cycle:** monthly (the only expiry that exists). One state-machine step per option expiry.
- **Entry:** first 5-minute bar at or after 09:30 IST on the trading day nearest on or before (option expiry minus 21 calendar days). Fill at that bar's open minus slippage. (The series exists from about 4 weeks before expiry, so 21 days is always inside the listing window. Choose 21 by this reason, not by liquidity or price.)
- **State CASH:** sell the put at strike = spot-future x (1 - 2.4%), rounded **down** to a multiple of Rs 500. (2.4% = the NIFTY weekly 1.2% times the square root of 4 weeks, a time-scaling convention. Percentage only; I did not look at gold volatility.)
- **Assignment (put ITM):** you are long one GOLDM future at the strike. **Close it at the first bar at or after 09:30 on the next trading day** (the future is physically delivered if held to its expiry about 4 trading days later). Cost: one futures round trip. Realised loss = (strike - exit price) x Rs 10 per Re 1. Then return to CASH and sell the next put at the next cycle.
- **Decision for you before pre-registering:** (A) **short-put-only with immediate close of the devolved future** (recommended: no delivery risk, cleanest test; this is Batch 4 control 1), or (B) a true wheel that **holds** the long future and sells a call against it (strike = spot-future x (1 + 2.4%), rounded **up** to a multiple of Rs 500; call ITM means you are short the future at the strike and close it the next trading day). Variant B means holding a physically deliverable future across the month and rolling it onto the next series, so its delivery and margin rules (not verified) become part of the strategy.
- **Costs:** use the table in section 5, with slippage of Rs 0.50, 1.00 and 1.50 per 10 g of option premium per fill (0.50 = one tick, primary 1.00). The repo's frozen NIFTY cost model cannot be reused; a separate gold cost module is needed and must be written before the run. CTT on exercised intrinsic value: unknown, run both with and without it.
- **Benchmark:** long 1 lot GOLDM future from the first entry, rolled on the 3rd business day before expiry, same costs.
- **Pass rule:** copy Batch 4 (block bootstrap, alpha corrected for the trial count at that time) but note that with monthly data the blocks of 5 should become 3 months and power is low; a pass is practically impossible below about 40 cycles.

## 7. Verified vs assumed

**Verified today (live source, 2026-10-18):** which gold contracts exist and which have options (Upstox); lot sizes and multipliers (Upstox); Rs 500 strike steps and monthly-only expiries for today's listed series (Upstox); options are on futures and devolve into futures, European style, ITM auto-exercise, ATM expires worthless (MCX web pages); expired-instrument APIs return nothing for MCX (docs + real calls); active-contract 5-minute and daily candles with OI exist but start only with the current listing (probe); broker-page cost rates on Zerodha's page.

**Assumed or not verified:** Upstox's own commodity brokerage row; MCX's own charge circulars; CTT on exercised options; any change to CTT in Budget 2026; the Gold Mini option expiry rule and why Dhan shows one day earlier than Upstox; MCX tender-period dates and delivery-period margin for GOLDM; the Gold Mini option launch date and any earlier strike-interval changes; the MCX Bhav Copy as a data route; that Upstox's lot sizes held for past years (no history to check).
