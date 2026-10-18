"""Settings and file locations for the idea-factory loop (docs/ideas/LOOP_SPEC.md). PAPER BOOKKEEPING ONLY: nothing here
places orders. Every limit the owner may want to change is in this one file. Dev data only; the hidden holdout is never read."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDEAS = HERE.parent
RESEARCH = IDEAS.parent
REPO = RESEARCH.parent

# --- the multiple-testing rule (spec step 3)
FAMILY_ALPHA = 0.05  # alpha for a batch = FAMILY_ALPHA / (total trials ever, including the batch being run)
MAX_BATCH = 10
DEFAULT_COST = 0.001  # 0.10% of notional per round trip, same as Batch 1
MIN_DEV_TRADES = 60  # same as Batch 1 pass rule (e)

# --- forward -> promoted (spec step 4)
FWD_MIN_DAYS = 60  # forward trading days (settled, eligible start days)
FWD_MIN_TRADES = 20  # ADDED by the builder: a sparse idea with 3 trades in 60 days proves nothing
FWD_ALPHA = 0.05  # bootstrap p and random-entry p, forward days only

# --- retire (spec step 5)
RETIRE_WINDOW = 40  # rolling forward days
RETIRE_DD_MULT = 2.0  # retire if forward drawdown > this x dev drawdown

# --- paper book filters on promoted ideas (spec step 5). Rupee figures are ASSUMPTIONS the owner should check.
LOT_NOTIONAL_RS = 1_500_000  # ASSUMED value of one NIFTY futures lot (lot size x index level); verify before reading rupee figures
SIZE_CAP_LOTS = 1  # size cap: never more than 1 lot equivalent per idea
DAILY_LOSS_LIMIT_RS = 15_000  # ASSUMED 1% of one lot; a day that loses more pauses new entries the next trading day
PORTFOLIO_CAP = 3  # most positions open at the same time across all promoted ideas

# --- data files the dev test and the dry run read (the same dev files Task 5 used)
DEV_FILES = {"daily": "nifty_day_dev.csv", "vix": "india_vix_day.csv", "m5": "nifty_5minute_dev.csv"}
CLOSE_IST_MINUTES = 15 * 60 + 45  # live mode refuses to run before 15:45 Indian time (market closes 15:30)


@dataclass
class Paths:
    registry: Path = HERE / "registry.jsonl"
    ledger: Path = HERE / "ledger_loop.jsonl"
    forward_log: Path = HERE / "forward_log.csv"
    results: Path = HERE / "results"
    dev_dir: Path = RESEARCH / "data"
    batch1_results: Path = IDEAS / "results" / "ideas_batch1_results.json"
    batch1_md: Path = REPO / "docs" / "ideas" / "IDEAS_BATCH1_2026-10-18.md"
    ideas_docs: Path = REPO / "docs" / "ideas"
    extra: dict = field(default_factory=dict)


PATHS = Paths()
