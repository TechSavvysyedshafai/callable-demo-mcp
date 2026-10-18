---
name: research-reporting
description: Use when reporting results, writing RESULTS.md entries, weekly notes or answering the owner. Plain language, answer first, numbers with caveats, one next step.
---

# Research reporting

The owner is new to coding and markets and decides with their own money. Write for them.

## Shape of every report
1. **Answer first**, one or two sentences: did it work, yes/no/unclear, and what it means for their money.
2. **The numbers** in a small table: net P&L after costs, trades, win rate, gross points per trade vs break-even points, p-value vs random, trials so far.
3. **What is verified / assumed / unknown.** Name each assumption (for example "spread is assumed Rs0.10").
4. **Adversarial-review verdict** (REJECT / INCONCLUSIVE / SURVIVES REVIEW + gate step).
5. **One next step**, with who does it. Not a menu of ten.

## Style
- Short sentences. Explain any term the first time (STT, slippage, p-value, holdout). No hype words ("promising", "great").
- Negative results get the same space and clarity as positive ones. A failure is progress: say what it saved them.
- Never paste secrets, tokens or personal data. Mark guesses as guesses.
- Keep `research/RESULTS.md` as the dated source of truth (Planned -> Result), one entry per test, newest last.

## Weekly note (one page)
Done this week | Results (with verdicts) | What we now believe | Risks / things that might be wrong | Decision needed from the owner.
