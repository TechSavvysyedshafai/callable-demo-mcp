# Repo rules for any coding agent (read first)

This repo is a research lab for Indian index markets (NIFTY first), plus an MCP data server. It places **no real orders**.
Your role when doing research is defined in `docs/quant-researcher/CHARTER.md` and `.claude/agents/quant-researcher.md`.

Non-negotiable rules
1. **No order placement code, ever**, and no live trading. Paper trading only. Real money needs the owner's explicit written approval.
2. **Never read, print, copy or commit secrets** (API keys, access tokens, `UPSTOX_ANALYTICS_TOKEN`, `KITE_*`). Tokens live only in environment variables.
3. **The hidden holdout (`~/.nifty_holdout`) is off limits** to research. Only `final_holdout.py` scripts touch it, once, when the owner says so.
4. **Frozen files are not edited to make a result look better**: `research/harness.py`, `research/scalp/engine.py`, `*/backtest*.py`, cost models, tests.
   Fixing a real bug is allowed, but state it plainly in the report and re-run everything affected.
5. **Pre-register before you run**: hypothesis, metric, data window, max trials, pass criteria. Every distinct strategy version is a trial; it is logged in `ledger.jsonl`.
6. **Report negative results as plainly as positive ones.** Append every test to `research/RESULTS.md`.
7. **Say what is verified and what is assumed.** Rates, lot sizes and expiry rules change; verify against the broker/exchange page and cite the date.
8. Keep explanations simple: the owner is new to coding and markets.

Map of the repo: `research/` daily forecast lab; `research/scalp/` futures scalp + paper trading + champion/challenger;
`research/scalp/options/` option scalp (model-based and real-candle backtests); `research/upstox/` data adapter (preferred data source);
`src/` Cloudflare Worker MCP server (Zerodha tools). Tests: `research/**/tests/*.py` (run them before and after changes).
