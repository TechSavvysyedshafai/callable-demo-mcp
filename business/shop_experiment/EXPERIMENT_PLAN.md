# Shop experiment plan: "Kerrova" jeans and T-shirt shop, Patna (written BEFORE starting)

Simple words on purpose. Edit the shop name and numbers in the brackets if they are wrong.

## The question
Do a few cheap changes bring more customers to the shop, and which ones? We do NOT assume they work. We count, and we keep only what the numbers support.

## What we count every day (5 minutes at closing time)
Fill one row in `daily_log.csv` (or a Google Sheet with the same columns):
- date, phase (baseline / A / B / C)
- walk_ins: people who came in (one person tallies at the door with a counter app or pen marks)
- bills: number of bills made that day
- sales_rs: total sales in rupees
- exchanges: number of swaps or returns
- festival: 1 if it is a festival, wedding rush or bandh day, else 0
- src_google, src_whatsapp, src_instagram, src_friend, src_passing, src_other: how many new customers said they came because of each (ask every NEW customer at the bill: "How did you hear about us?")
- notes: anything unusual (rain, power cut, big sale next door)

Also keep the lost-sale sheet (`print/lost_sale_sheet.html`): every time someone asks for something you do not have, write one line.

## The phases (each change is added on top of the earlier ones)
| Phase | Days | What changes | Cost |
|---|---|---|---|
| baseline | 1-7 | NOTHING. Just count. | 0 |
| A | 8-21 | Counter sign: "Try anything on. Swap within 7 days with your bill." Tape-measured size tags on your 20 best lines. Only if you really keep the promise. | tags and a tape: a few rupees |
| B | 22-35 | Add: Google Business Profile live, ask happy customers for reviews, a WhatsApp message to past customers WHO AGREED (consent form), WhatsApp Business app greeting. | 0 |
| C | 36-49 | Add: student offer (your choice of offer) with a poster at coaching centres and hostels. | the discount you give |
| Optional stock test | after day 49 | Only if the lost-sale sheet shows the SAME gap again and again: order about 50 T-shirts and 24 jeans of that type from a supplier that states fabric weight (about Rs 17,600-18,600 in the research, my arithmetic, unverified). | stock |

Why one at a time: if everything changes on one day, you will not know what worked. Why stack them: a single shop cannot run two separate shops. Honest limit: there is no control shop, so season, weather and festivals can fool us. That is why festival days are marked and left out, and why we compare each phase to the same weekdays of the baseline week.

## The score (decided now, not after seeing results)
- Main number: bills per day.
- For each treatment day we compare with the baseline average for the same weekday. Lift = how much higher (or lower) the bills were than that baseline, on average.
- KEEP a change if the lift is at least +10% AND the "80% range" for the lift (computed by the script) is above zero.
- DROP it (stop doing it, or change it) if the lift is below +10%, or the range includes zero. If it is unclear, repeat 7 more days once, then decide.
- Also watch: sales in rupees per day (a change that adds bills but cuts the average sale may not help), exchanges (should stay under 10% of bills), conversion (bills per 100 walk-ins).
- The +10% is a number I picked. Change it to what would make the effort worth it for you, BEFORE you start.

## Hard rules
- Message customers on WhatsApp only if they agreed (consent form). At most one message per week. Handle every STOP the same day.
- Do not buy or write fake reviews.
- Do not change the plan after seeing results. If you want a new idea, write it as a new phase.
- Do not put passwords, OTP codes or card numbers into any file or chat.

## Honest limits
- One shop, a few weeks: the numbers will be noisy. A small lift will not show up clearly.
- Counting walk-ins is hard; use a simple clicker and accept errors.
- The research behind this plan is thin on Patna itself (see business/shop_research/REPORT.md).
- If nothing helps, that is an answer too: the problem may be price, location or a mall nearby, and we then look at the bills (what sells, what sits) for the next experiment.

## How to read the results
Run `python3 analyze.py daily_log.csv lost_sales.csv` (needs Python 3 only). It prints a table per phase, the lift, the range, the top lost-sale gaps and a plain verdict for each change.
