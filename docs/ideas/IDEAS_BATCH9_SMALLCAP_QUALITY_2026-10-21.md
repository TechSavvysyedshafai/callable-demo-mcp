# Batch 9: small-cap quality screen, India (pre-registered 2026-10-21, BEFORE any test or pilot number)

## Hypothesis
Among NSE small caps, companies with high return on equity, low debt and positive profit growth beat the small-cap index over the following year, after costs and after correcting for survivorship bias.

## Scope limits (honest)
- Small-cap universe: NSE Smallcap 250 constituents AS OF EACH REBALANCE DATE (point-in-time), not today's list. Today's list would hide every small cap that failed or was delisted, and that bias would make the screen look good.
- Data: company financials from Fiscal-AI (coverage for Indian small caps NOT yet verified: the pilot must confirm it); daily prices from Upstox equity candles (NSE_EQ). Any stock with missing data on a date is excluded from that rebalance and the exclusion is counted.
- Window: whatever the verified data supports. Pilot first. Full test only if coverage passes the pilot.

## Rules (fixed)
1. **Quality filter, evaluated at each annual rebalance (1 April):** using only fiscal years that ended before the rebalance date:
   - return on equity >= 15% in each of the last 3 fiscal years;
   - debt-to-equity <= 0.5 in the last fiscal year;
   - net profit higher in the last fiscal year than 3 years earlier.
2. **Rank** survivors by the last fiscal year's ROE, highest first. **Hold the top 20**, equal weight, from the first trading day after the rebalance date to the next rebalance date.
3. **If fewer than 20 pass,** hold however many pass. If none pass, hold cash (earns 0).
4. **Benchmark:** the Nifty Smallcap 250 index (total return), held over the same dates.
5. **Costs:** delivery buy and sell at the published Shoonya rates (STT 0.1% each side, stamp duty 0.015% on buy, exchange charges, GST), plus 0.20% per side for spread and slippage. Rebalancing turnover is charged in full.
6. **Test:** annual excess return of the screen over the benchmark, after costs. One-sided bootstrap p-value (blocks of 2 years, 10,000 resamples) for mean excess > 0.

## Pass rule (all must hold)
- Mean annual excess return after costs > 0.
- p < 0.05 / 15 = 0.0033 (this is trial 15 across the lab's ledger, counting the Batch 4 wheel and the earlier ones; covered-call test not yet run).
- Positive excess return in both halves of the sample (split at the calendar midpoint).
- Result holds with survivorship-corrected constituents only. A result that appears only with today's list is reported as NOT a pass.

## Controls (reported, not trials)
- **Random portfolio:** 20 small caps chosen at random from the same point-in-time universe each year, same costs. Shows whether the screen adds anything over random small caps.
- **Quality filter without the ROE rule** (debt and profit-growth rules only): does ROE matter?

## Negatives and failures
Every rebalance date, every excluded stock and its reason is listed. Delisted or suspended stocks are kept in the test with their last available price, not dropped. All results are reported as plainly as positives.

## Verdict rules
- PASS: all four pass conditions hold.
- INCONCLUSIVE: positive mean excess but p or the halves test fail.
- REJECT: otherwise.
- Pilot (3 stocks) is a feasibility check only. It produces no trial and no return number.

## Pilot (feasibility only, not a trial)
Three small-cap stocks, chosen before looking at their numbers: check that (a) Fiscal-AI returns 5 fiscal years of ROE, debt and profit for Indian companies, (b) Upstox returns daily equity candles back to 2014 for NSE_EQ keys. Report coverage gaps. No return is computed.

## Pilot result (2026-10-21, feasibility only, no trial, no return computed)
- Stock checked: Reliance Industries (large cap; small caps not yet checked). Chosen before any data was pulled.
- (a) Fiscal-AI financials: FAIL. The profile is found (Indian company, NSE primary listing, INR reporting), but its available datasets are only events_calendar, fund_letters, investor_relations, news and segments_and_kpis. No income statement, balance sheet or cash flow is listed, so ROE and debt cannot be computed from it.
- (b) Upstox daily prices: PASS for Reliance. Regular equity candles (historical-candle endpoint, NSE_EQ key) return daily bars back to 2015. The expired-instruments endpoint rejects equity keys, so the regular endpoint must be used for stocks.
- Consequence: the quality screen cannot run on the current data. Rules 1 and 2 need annual ROE and debt per company. A financials source with Indian statements is required before the full test. Trial counter unchanged at 14.
