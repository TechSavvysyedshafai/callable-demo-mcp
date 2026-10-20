# Customer-finding test: "Shop Starter Kit" (pre-registered, written BEFORE any traffic)

Not tied to the Patna shop. The product is only a test subject.

## Product (the thing we are testing demand for)
"Shop Starter Kit": for a small local shop in India, a done-for-you setup of (1) a Google Business Profile, (2) the free WhatsApp Business app profile, greeting and quick replies, (3) a consent form and a weekly message plan, written in Hindi and English. We do NOT sell anything yet. We only measure whether real shop owners show interest.

## Question
Will small shop owners who see an honest page about this kit (a) leave their contact details, and (b) say they would pay for it?

## What we measure (per channel, with UTM tags)
- visits (people who open the page)
- signups (they fill the form AND tick the consent box)
- price_intent: which option they choose: "free guide only", "Rs 299", "Rs 999", "Rs 2,999 done-for-you setup"
- their open answer: "What is your biggest problem getting customers?"

## Channels (honest, no spam)
Posts in groups where the group rules allow it, LinkedIn, Instagram or Facebook posts and reels from the owner's own accounts, a few direct introductions through people we know, and local shop-owner communities. No bought lists. No messages to people who did not ask. No fake testimonials, no fake numbers.

## Rules fixed in advance (my picks, change them BEFORE starting if you disagree)
- Run for 14 days or until 300 visits, whichever is later; at most one extension of 7 days.
- PASS needs both: signup rate >= 8% of visits AND >= 25% of signups pick a paid option (Rs 299 or more).
- If visits < 300 after the extension: INCONCLUSIVE (not enough traffic), not a fail.
- If signup rate < 3%, or fewer than 10% of signups pick a paid option: FAIL, stop.
- In between: one change to the page copy or channel, 7 more days, then decide.
- The script prints Wilson 95% ranges, so you can see how uncertain the rates are.
- These thresholds are guesses, not benchmarks from data.

## Hard rules
- Only collect contact details with the consent box ticked, and store the consent date and source.
- Message people only through the consent-first tool in `messenger/` (dry run by default, weekly cap, quiet hours, STOP honoured).
- Never put passwords, OTP codes or card details anywhere.
- Say plainly on the page that this is a test and that nothing is charged.

## What a PASS means and does not
A PASS means "worth building a small version and charging for it". It is not proof of a business. A FAIL costs us nothing but time.
