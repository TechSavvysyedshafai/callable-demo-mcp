# Idea factory loop: spec (owner said "go" on 2026-10-18). Paper only.

Funnel: GENERATE -> DEV TEST (once) -> PAPER FORWARD (fresh days) -> PROMOTE (paper size, filters) -> real money only with owner's written approval.

1. Registry: research/ideas/registry.jsonl. One line per idea: id, rule (machine-readable), forced-trader story, created date, status (proposed/tested/rejected/forward/promoted/retired).
2. Generate: a weekly batch of up to 10 ideas written BEFORE testing (human or AI proposes; never auto-selected by results). No idea is a variant of a tested idea (change of threshold = new trial and counts).
3. Dev test: same runner and pass rule as Batch 1, run once per idea. Global trial counter across ALL batches; alpha for a batch = 0.05 / (total trials so far, including this batch). Ledger append-only.
4. Forward paper: a daily job (after market close, uses Upstox daily/5-min data) computes each forward idea's signal for the day and records paper P&L net of the batch cost. No re-tuning. Idea forward-promotes after >= 60 trading days with net mean > 0, bootstrap p < 0.05 on fresh days only, and beating the random-entry null.
5. Filters on promoted ideas (paper): size cap 1 lot equivalent, daily loss limit, auto-retire if rolling 40-day net mean < 0 or drawdown > 2x its dev drawdown, one position per idea, no overlap beyond a portfolio cap.
6. Report: weekly plain-English summary (answer first): tests run, survivors, forward status, paper P&L, what got retired.
7. Scheduling: the daily job is a script in research/ideas/daily_forward.py. Cron/schedule is set up only after the owner approves the script.
8. Hard limits: no order code, no secrets in files, holdout untouched until a promoted idea gets a single final_holdout run when owner says so.
