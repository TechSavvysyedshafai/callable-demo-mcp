"""Weekly plain-English report, answer first. Read-only: it changes no idea, no log, no ledger; it only writes results/WEEKLY_<date>.md.

  python weekly_report.py                  # week ending today
  python weekly_report.py --asof 2026-11-01

Sections: the answer in a few lines (tests run, survivors, forward status, paper P&L, retired), then the table behind each line, then limits."""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import daily_forward as df_  # noqa: E402
import loop_config as cfg  # noqa: E402
import promotion as pr  # noqa: E402
import registry as reg  # noqa: E402
import trial_ledger as tl  # noqa: E402


def _in_week(ev: dict, asof: date) -> bool:
    return asof - timedelta(days=7) < date.fromisoformat(ev["date"]) <= asof


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def build(asof: date, paths=None) -> str:
    p = paths or cfg.PATHS
    bad = reg.problems(p)
    evs = tl.read(p)
    rows = reg.load(p)
    log = df_.read_log(p.forward_log)
    trials_week = [e for e in evs if e["event"] == "trial" and _in_week(e, asof) and "source" not in e]
    survivors = [e for e in trials_week if e["verdict"] == "SURVIVES"]
    moves = [e for e in evs if e["event"] == "status" and _in_week(e, asof)]
    went_promoted = [e for e in moves if e["to"] == "promoted"]
    went_retired = [e for e in moves if e["to"] == "retired"]
    fwd = [r for r in rows if r["status"] == "forward"]
    prom = [r for r in rows if r["status"] == "promoted"]
    decisions = {d["id"]: d for d in (pr.decide(r, log, asof) for r in fwd + prom)}
    book = pr.book_for(rows, log, asof)
    week_cut = pd.Timestamp(asof - timedelta(days=7))
    pnl_total = float(book["pnl_rs"].sum()) if len(book) else 0.0
    pnl_week = float(book[book["exit_date"] > week_cut]["pnl_rs"].sum()) if len(book) else 0.0
    n_total = tl.total_trials(p)
    skipped = book[book["status"] != "taken"] if len(book) else book

    A = []
    A.append(f"- **Tests run this week:** {_plural(len(trials_week), 'new idea')} tested once each ({n_total} trials counted in total since the start). "
             + (f"Survivors: {', '.join(e['idea_id'] for e in survivors)}." if survivors else "Survivors: none."))
    promo_txt = (f"Promoted this week: {', '.join(e['idea_id'] for e in went_promoted)}." if went_promoted else "None promoted this week.")
    if fwd:
        far = max(decisions[r["id"]]["stats"]["days"] for r in fwd)
        A.append(f"- **Forward test (fresh days, paper):** {_plural(len(fwd), 'idea')} running; the furthest has {far} of the {cfg.FWD_MIN_DAYS} days needed. {promo_txt}")
    else:
        A.append(f"- **Forward test:** no idea is running forward right now ({len(prom)} promoted in total). {promo_txt}")
    A.append(f"- **Paper P&L:** Rs {pnl_week:,.0f} this week, Rs {pnl_total:,.0f} since promotion, on {_plural(int((book['status'] == 'taken').sum()) if len(book) else 0, 'paper trade')}"
             f" (rupee figures assume one lot is worth Rs {cfg.LOT_NOTIONAL_RS:,}; this is bookkeeping, not money).")
    A.append("- **Retired this week:** " + ("; ".join(f"{e['idea_id']} ({e['reason']})" for e in went_retired) if went_retired else "none."))
    verdict = ("No new edge found this week." if not survivors and not went_promoted else
               "Something moved this week - read the table below before believing it; one pass at these odds is still more likely luck than edge.")
    nxt = cfg.FAMILY_ALPHA / (n_total + cfg.MAX_BATCH)
    L = [f"# Idea factory: weekly note, week ending {asof}", "", f"**Answer: {verdict}** Nothing here involves real money; the owner has not approved any trading.", "", *A, "",
         f"The bar for the next batch of 10 ideas is p < {nxt:.5f} (0.05 divided by {n_total + cfg.MAX_BATCH} trials), so each new batch is harder to pass than the last.", ""]
    if bad:
        L += ["**WARNING - the registry and the ledger disagree:** " + "; ".join(bad), ""]
    L += ["## Ideas by status", "", "| Status | Ideas |", "|---|---|"]
    for s in reg.STATUSES:
        ids = [r["id"] for r in rows if r["status"] == s]
        L.append(f"| {s} | {len(ids)}{(': ' + ', '.join(ids)) if 0 < len(ids) <= 12 else ''} |")
    if fwd or prom:
        L += ["", "## Forward and promoted ideas (fresh days only)", "",
              "| Idea | Status | Forward days | Trades | Mean net/trade | Boot p | Random-entry p | Drawdown | Next step |", "|---|---|---|---|---|---|---|---|---|"]
        for r in fwd + prom:
            d = decisions[r["id"]]
            s = d["stats"]
            mean = "n/a" if s["mean_net"] != s["mean_net"] else f"{s['mean_net'] * 100:+.3f}%"
            L.append(f"| {r['id']} {r['name']} | {r['status']} | {s['days']} | {s['trades']} | {mean} | {s['boot_p']:.3f} | {s['null_p']:.3f} | {s['drawdown'] * 100:.2f}% | {d['reason']} |")
    if len(skipped):
        L += ["", "Paper trades skipped by the filters: " + ", ".join(f"{k} {v}" for k, v in skipped["status"].value_counts().items()) + "."]
    L += ["", "## What this does and does not tell you", "",
          "- Daily data only goes back to 2018-10 and 5-minute / VIX data to 2023-10, so dev tests are short; forward days are the real filter.",
          "- Overnight drift was real before costs in Task 5 but costs removed 88% of it.",
          "- Fills are assumed at the stated print with a flat round-trip cost; real orders would do worse. Rupee P&L uses an assumed lot value.",
          "- Reaching `promoted` only means the idea survived 60 fresh days on paper. Real money needs the owner's written approval and the hidden-holdout run."]
    return "\n".join(L) + "\n"


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--asof")
    a = a.parse_args()
    asof = date.fromisoformat(a.asof) if a.asof else date.today()
    text = build(asof)
    cfg.PATHS.results.mkdir(parents=True, exist_ok=True)
    out = cfg.PATHS.results / f"WEEKLY_{asof}.md"
    out.write_text(text)
    print(text)
    print("written:", out)


if __name__ == "__main__":
    main()
