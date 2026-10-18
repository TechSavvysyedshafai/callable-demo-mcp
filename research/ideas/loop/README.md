# The idea factory loop (paper only)

This is the machine described in `docs/ideas/LOOP_SPEC.md`. It takes trading ideas, tests each one exactly once on old data, then watches the survivors on new days with pretend money. It places **no orders**, holds **no passwords**, never opens the hidden holdout, and **nothing here runs by itself**: there is no schedule. You (or I, when you say so) start each step by hand.

## The plain-language version

1. **Write ideas down first.** A batch is up to 10 new ideas, written in a dated file `docs/ideas/IDEAS_BATCH<N>_<date>.md` *before* anything is tested, and added to the registry (`registry.jsonl`). Each idea has a rule written so a computer can run it, a one-line story (who is forced to trade, and why they lose), and a fingerprint of the rule.
2. **Test each idea once.** The batch runner applies the same pass rule as Batch 1. The bar gets harder every time: for a batch, the allowed fluke chance is `0.05 ÷ (every idea ever tested, including this batch)`. Batch 1 was 10 ideas, so 0.005. A second batch of 10 must beat 0.05 ÷ 20 = **0.0025**, a third 0.05 ÷ 30, and so on. Changing a number inside an old idea is **not** allowed to be a quiet tweak: it is a new idea and counts as a new test.
3. **Survivors go to the "forward" list.** Ideas that fail are closed for good (status `rejected`).
4. **Forward days.** Every day after the market closes, the daily job works out what each forward idea would have done that day, using only information known then, and writes the pretend result (after costs) into `forward_log.csv`. It never changes a rule.
5. **Promotion.** An idea becomes `promoted` only after at least 60 forward trading days where: it made money on average after costs, a bootstrap test gives p < 0.05 on the forward days alone, and it beat random entries. (I added one extra guard: at least 20 forward trades, because three trades in 60 days prove nothing.) Promoted ideas are tracked in a **paper book** with limits: 1 lot at most, one position per idea, at most 3 open positions at once, and a pause on new entries after a bad day.
6. **Retirement.** A promoted idea is retired if its last 40 forward days lost money overall, or if its drawdown (biggest fall from a peak) becomes more than twice what it had in the old-data test.
7. **Weekly note.** One page in plain English, answer first.

Real money is a separate decision that needs **your written approval** and a single run on the hidden holdout when you say so. Nothing in this folder can do that.

## The files

| File | What it is |
|---|---|
| `registry.jsonl` | One line per idea: id, rule, story, created date, status, rule fingerprint. Seeded with the 10 Batch 1 ideas, all `rejected`, with their Task 5 numbers. |
| `ledger_loop.jsonl` | Append-only diary of every registration, batch start, test and status change. Each line carries a fingerprint of the line before it, so editing history is detected. The trial counter is the number of `trial` lines (10 now). |
| `forward_log.csv` | Append-only paper results, one row per idea per forward day. Created by the daily job (does not exist until the first forward day). |
| `loop_config.py` | Every limit in one place (60 days, the lot value, the loss limit, the position cap). |
| `registry.py`, `trial_ledger.py`, `rule_engine.py`, `batch_runner.py`, `daily_forward.py`, `promotion.py`, `weekly_report.py`, `loop_stats.py` | The code. `tests/` has the checks. |
| `results/` | Batch results, the paper book and the weekly notes (created when used). |

## How you run it (copy and paste)

All commands are run from the repo folder. Replace the batch number and date.

```bash
# 0. See where things stand
python research/ideas/loop/registry.py list
python research/ideas/loop/registry.py check          # "consistent" means nobody edited history

# 1. Add the ideas of a new batch (each in its own small .json file: id, batch, name, story, rule, cost)
python research/ideas/loop/registry.py register my_idea.json     # add --allow-variant only if it is a changed version of an old idea (counts as a new test)
python research/ideas/loop/registry.py md-row B2-01              # prints the line to paste into the dated IDEAS_BATCH file
#    Write docs/ideas/IDEAS_BATCH2_2026-10-25.md with every idea's row, then commit it BEFORE step 2.

# 2. Run the batch (once). Needs the dev data in research/data (research/upstox/fetch_upstox.py makes it)
python research/ideas/loop/batch_runner.py --batch 2 --md docs/ideas/IDEAS_BATCH2_2026-10-25.md

# 3. Every trading day, after 15:45 India time (needs UPSTOX_ANALYTICS_TOKEN set in your terminal, never in a file)
python research/ideas/loop/daily_forward.py
#    Practice run on old data, writes to a scratch folder, never the real log:
python research/ideas/loop/daily_forward.py --dry-run --asof 2026-03-02 --ideas B2-01

# 4. Check for promotions and retirements (add --apply to write them)
python research/ideas/loop/promotion.py
python research/ideas/loop/promotion.py --apply

# 5. Weekly note
python research/ideas/loop/weekly_report.py
```

The batch runner **refuses** (and logs nothing) if: a rule was edited after registration, the dated markdown file is missing, mis-named, dated in the future or does not show each idea's fingerprint, or the history file was tampered with. Running the same batch twice does nothing the second time. If a run crashes halfway, running it again finishes only the ideas not yet tested, at the same alpha.

## Honest notes (please read)

- **Short data.** Daily data only goes back to 2018-10 and 5-minute / VIX data to 2023-10, so the old-data tests are short and easily fooled. The forward days are the real filter.
- **Overnight drift** was real before cost in Task 5, but costs removed 88% of it. Batch 1: all 10 rejected. This loop has not found an edge; it is machinery for testing ideas honestly.
- **Forward days start after the idea does.** Each forward idea has a `forward_since` date (the day of its batch run). Days before it never count, so the old-data period cannot leak into the forward record. The hidden holdout months (roughly April to October 2026, as I infer from the dev data ending 2026-04-16) are in the past now; the daily job only fetches a short history before `forward_since` to compute things like a 5-day return, and records nothing from before it. If you want the holdout to stay untouched in the strictest sense, start the forward test with a `forward_since` of today or later (this is already how it works) and note that those few lookback bars were fetched.
- **Rupee figures are assumptions.** `LOT_NOTIONAL_RS` (Rs 15 lakh per lot) and the loss limit are placeholders. NIFTY's lot size changes; check the NSE page before you read any rupee number. Percentages are what the tests judge.
- **Fills.** The tests assume trades happen exactly at the stated price (open or close) with a flat round-trip cost (0.10% by default). Real orders would do a little worse. Task 5 showed a gap-fade idea that only worked at the very first print.
- **Sparse ideas** (a rule that fires a few times a year) will sit in `forward` for a long time. That is correct, not a bug.
- **Scheduling.** Nothing is scheduled. When you approve the daily script, a cron / scheduled task can call `daily_forward.py` and `promotion.py --apply` after 15:45 India time on trading days. I have not set that up.

## Checking the machine

```bash
python research/ideas/loop/tests/test_loop_core.py
python research/ideas/loop/tests/test_loop_batch_forward.py
python research/ideas/loop/tests/test_loop_promotion_report.py
```
These use made-up data with a known built-in edge, so the answers are known in advance (hand-computed cases, idempotency, refusal after a rule change, shrinking alpha, edge cases of the promotion and retirement rules, and a scan of the code for holdout / order / password strings).
