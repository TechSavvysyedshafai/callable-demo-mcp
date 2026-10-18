# "Intraday delta neutral" as taught by Reyaansh Upadhyay (Theta Gainers) - derived rules

Source: YouTube, "Intraday se badhiya paisa banane wali Best Strategy | Delta Neutral Option Strategy | Theta Gainers",
https://www.youtube.com/watch?v=L5CFrgSK8wY (uploaded 2023-07-22, about 537k views). Read from the machine-generated transcript on 2026-10-18;
the transcript is auto-translated, so wording is uncertain in places (flagged below). He demonstrates on BANK NIFTY weekly options (Thursday expiry at
that time). The channel promotes its own algo platform and courses (commercial interest); a separate interview is titled "makes 4% return every month"
(about his monthly version; unverified marketing claim). We test the logic as an idea; we do not endorse any claim.

## Rules as taught (numbered)
1. **Find a sideways zone ("swing range")** from the last 2-3 days on the 15-minute chart: a support (where price turned at least twice) and a resistance
   (turned at least twice), e.g. Bank Nifty 45,300-45,800 (about 1.1% wide). Trade only if the market is INSIDE the zone. (Discretionary: drawn by eye.)
2. **Wait until about 9:30-9:45.** Skip the first 15-20 minutes (algo straddle entries at 9:20/9:25 make candles erratic).
3. **Entry (about 9:45, before 10:00):** sell the 25-delta call and the 25-delta put ("a bit below 25, never above"), same weekly expiry. One lot each.
   Nothing is bought: **there is no hedge/wing in the intraday version.** (His monthly version converts to an iron fly later; the intraday version does not.)
4. **Adjustment "25x25":** whenever either sold leg's price rises 25% above its reference price (initially its sale price), buy back the other (decayed,
   profitable) leg and sell a NEW option on that side whose premium is about equal to the risen leg's premium (re-match premiums, "make it delta neutral again").
   After matching, both legs' reference becomes the new matched price (example: ~135 each, next trigger ~168). Repeat.
5. **Straddle stage:** the matched strikes converge, typically Wed/Thu, to the same strike (a short straddle). Then put a **30% stop-loss on both legs**
   (example: 200 -> SL 260). If either stop hits, exit everything for the day.
6. **Range exit:** if the market leaves the zone, the non-directional trade ends. Base rule: exit (the video's example exits at a loss of about Rs1,247/lot).
   He insists on a "confirmed breakout" (consolidation then a red/green candle sequence on 15-minute candles); without confirmation he keeps the position.
   **Optional tweak (his advice, riskier):** on a confirmed breakout, cut the threatened leg and keep the other leg with a cost-to-cost stop (exit if it
   returns to the price at which it was sold) - converting to a directional trade.
7. **Exit** by about 15:15-15:20 the same day (intraday).
8. Examples shown: one calm day +Rs1,400/lot with no adjustment; one trending day -Rs1,247/lot. Margin quoted: about Rs1.0-1.2 lakh per lot (unverified).

## Interpretations we must make (mechanical proxies for the discretionary parts; fixed before testing)
- Swing range: 15-minute fractal swings (bar high/low that is the extreme within 3 bars each side) from the previous 3 sessions; resistance = nearest swing high above
  the 9:45 spot, support = nearest swing low below it; require both and a width of 0.4%-1.5% of spot; else no trade that day.
- Confirmed breakout: two consecutive 15-minute closes beyond the same boundary.
- 25-delta strike: Black-Scholes delta using each strike's own implied volatility inverted from its real candle price; pick the strike with |delta| nearest to but not above 0.25.
- Price/mark = last known 5-minute candle close; actions execute at the NEXT 5-minute candle open with slippage; missing candles are skipped and counted.

## Honest risk notes
- Naked short options have very large (theoretically unlimited) loss potential; the stops above limit but do not remove gap risk. Margin is large.
- Frequent adjusting multiplies brokerage, taxes (STT 0.15% of sell premium) and spreads, which can erase a small edge.
- One 2023 video on one index; the author's own later versions may differ.
