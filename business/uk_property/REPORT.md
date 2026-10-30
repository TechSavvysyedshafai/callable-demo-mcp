# UK property venture: deal model and stress test

Date: 30 Oct 2026. Files: `model.py` (run `python3 model.py`), `results.json`, `family_page.html`.
This is a simple model with assumed inputs. It is not advice and no real deal has been tested.

## Answer first
The first example deal on the family page (cash £55k, profit £130k) was too optimistic. With typical lender rules the same deal needs about £160k of cash and makes about £74k (10% of the sale value). A 10% fall in the sale price wipes out the profit.

## What was verified and what was assumed
Verified (lender pages, April to Oct 2026; secondary sources, not offers):
- Development loan: usually up to 65% of finished value (70% for experienced developers), up to 85 to 90% of cost, whichever is lower.
- Rates: 0.65 to 1.10% a month for residential new-build; first-time developers pay the top of the range (0.95 to 1.10%). Interest is rolled up and paid on exit.
- Fees: arrangement 1 to 2% (some say up to 3%), exit fee 1 to 2% at some lenders, broker about 1%, legal £5k to £12k, monitoring surveyor £750 to £3,000 a visit.
- Companies House identity verification is required for all directors, including those abroad (since 18 Nov 2025; one source).
- 2% stamp duty surcharge for non-UK-resident buyers of dwellings in England; a UK company can count as non-resident if non-residents control it (GOV.UK and adviser pages).
- Planning: England granted 87% of decisions in the year to Dec 2025; major housing schemes take over 300 days (a site citing official figures; not checked at source).

Assumed by me (not data): sale value £720k and cost £550k (from the family page), selling costs 2.5%, average 70% of the loan drawn, 15-month term, fixed fees £15k, and all stress ranges below.
Not verified: Personal Guarantee Insurance cover (the first page said "up to 80%"), lenders' minimum profit margins, how a development plot is classed for the stamp duty surcharge.

## Reconciling the first example
Family page: £720k - £550k - £39.6k (8% on a £495k loan for 12 months) = £130k. It left out selling costs, lender fees, the loan cap and a longer term.
The page's loan (£495k) is 69% of the sale value, above the usual 65% cap. At 65% the loan is £468k and the cash needed rises.

## Stress test (profit or loss, realistic case)
| Scenario | Profit |
|---|---|
| Base | +£74k |
| Sale price -5% / -10% / -15% / -20% | +£39k / +£4k / -£31k / -£66k |
| Build cost +10% / +20% | +£19k / -£36k |
| Delay +3 / +6 / +12 months | +£65k / +£55k / +£37k |
| Interest +2 points a year | +£66k |
| Bad mix (price -10%, cost +10%, 6 months late) | -£70k |
| Severe mix (price -15%, cost +15%, 9 months late, rate +2) | -£155k |
| Sale price -25% / -30% / -35% | -£102k / -£137k / -£172k, lender short by £5k / £40k / £75k |

Price fall that wipes out profit: 10.5%. Price fall at which the lender is not fully repaid (guarantee called): 24.4%.
Overruns are funded by the partners (the lender does not lend more), so cash in rises with costs: £215k at +10% cost, £270k at +20%.

## Risk quantification (20,000 random runs, my assumed ranges)
Ranges: price -15% to +5% (most likely 0), cost -2% to +25% (most likely +8%), delay 0 to 12 months (most likely 3), rate -1 to +3 points.
- Loss in about 70% of runs. More than half the cash lost in about 12%. All cash lost in about 0.1%. Lender shortfall in about 0%.
- Median result -£23k; 5th percentile -£101k; 95th percentile +£43k.
The cost skew (most likely +8%) drives much of this. Change the ranges in `model.py` to test your own view.

## Deal quality needed
| Sale value (cost fixed £550k) | Base profit | Share of sale value | Chance of a loss |
|---|---|---|---|
| £720k | £74k | 10% | 69% |
| £780k | £129k | 16.5% | 28% |
| £820k | £168k | 20.5% | 9.5% |
| £860k | £207k | 24% | 2% |
At £820k the deal still makes +£48k with price -15%, +£13k in the bad mix, and loses £78k in the severe mix.

## Mitigation, tied to the numbers
| Risk | Size in the model | Mitigation |
|---|---|---|
| Sale price falls | Profit gone at -10.5%; guarantee touched at -24% | Buy so planned profit is at least 20% of sale value; value on cautious comparable sales; consider pre-sale or rent-and-hold exit |
| Build cost overrun | +10% costs £55k more cash and cuts profit by £55k | Fixed-price contract, 10% contingency, monitoring surveyor, fund the overrun in advance |
| Delay (planning, build) | Each 3 months costs about £9k to £10k | Planning granted before purchase or conditional contract; 6 months of cash buffer |
| Interest | +2 points costs about £8k | Fix the rate; shorter term; compare lenders through a broker |
| Personal guarantee | Starts at about -24% price; £40k short at -30% | Capped guarantee, no-guarantee lender, Personal Guarantee Insurance (check terms), uncle takes independent legal advice |
| Cash cannot fund an overrun | Lender can enforce and sell the site | Hold reserve cash; do not start without it |
| Partner abroad | 2% stamp duty surcharge possible; ID verification; tax on UK board attendance | Adviser sign-off before the first purchase |

## Go / no-go rules for a first deal
1. Planned profit at least 20% of sale value.
2. Break-even or better at a 15% lower sale price.
3. Planning in place before purchase.
4. Fixed-price build plus 10% contingency.
5. Capped or no personal guarantee, in writing.
6. Uncle's own solicitor; accountant for the non-resident points.
7. One small deal, fully sold, before a second.

## Next steps
- Ask a development-finance broker for a real indicative term sheet on a real plot (free).
- Replace the sale value and cost with an actual plot's numbers and rerun `model.py`.
- Agree with the uncle what he will and will not sign before spending money on any deal.

## Lead checks (30 Oct 2026)
- L1 North Finchley plot (Friern Barnet Road): the auction was on 29 Jul 2026. Stale. Dropped.
- L2 Land rear of Howard Avenue, Bexley DA5 (planning 24/02599/FUL, 62 sq m bungalow): Sold STC at a guide of GBP 175-200k. Agent says GDV GBP 500-525k. Local data (ONS/HM Land Registry, Aug 2026): Bexley average GBP 415k; flats GBP 246k, terraced GBP 418k, semi GBP 536k, detached GBP 737k. A 62 sq m home at GBP 500k+ looks high; I have no sold-price evidence for this size.
- Cost used (assumptions): land GBP 190k, build 62 sq m x GBP 3,000 (Build It 2026: GBP 2,500-3,000 per sq m for self-build; small projects cost more per sq m), 15% fees and contingency, CIL GBP 7.4k, other GBP 15k = about GBP 427k before finance.
- Result: GDV GBP 400k = -GBP 77k; GBP 460k = -GBP 23k; GBP 512k (agent) = +GBP 25k (4.8% of sale value). 20% needs about GBP 630k. Fails the go/no-go rules.
- Flag: LandSale shows Flood Zone 3 about 20 m away (high river/sea risk). Needs a flood risk check.
