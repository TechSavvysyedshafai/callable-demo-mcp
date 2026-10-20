# customer_test: a customer-finding test plus a consent-first messaging tool

- `EXPERIMENT_PLAN.md`: the pre-registered test (read first).
- `landing/index.html`: an honest one-page site (English and Hindi), no third-party scripts. Set `FORM_ENDPOINT` inside it to a Google Apps Script or Google Form endpoint. Without it, the page runs in demo mode and stores answers only in the browser.
- `collector.gs`: a free Google Apps Script that stores page events and sign-ups in your own Google Sheet (10-minute setup, instructions inside).
- `funnel.py`: reads `events.csv` (date,channel,event[,price_choice]) and prints rates, uncertainty ranges and the PASS/FAIL/INCONCLUSIVE verdict.
- `messenger/messenger.py`: sends (or dry-runs) messages ONLY to contacts who consented, honours STOP, weekly cap, quiet hours and a per-run limit. It has no live sending; providers are an interface. The default writes an `outbox.csv` you can review.
- Tests: `python3 tests/test_funnel.py` and `python3 messenger/tests/test_messenger.py`.
Nothing here sends anything by itself.
