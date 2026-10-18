"""Promotion, retirement and the paper book (spec steps 4 and 5). Everything here is bookkeeping on the forward log: no orders, no broker.

  python promotion.py                 # show what WOULD change (nothing is written)
  python promotion.py --apply         # write promotions / retirements to the registry and ledger, rebuild results/paper_book.csv

forward -> promoted needs ALL of (forward days only, never the dev period):
  >= 60 forward days, >= 20 forward trades (added by the builder), net mean per trade > 0, bootstrap p < 0.05, random-entry p < 0.05.
promoted -> retired when EITHER: the last 40 forward days' net P&L is below zero (so the rolling 40-day net mean < 0),
  OR the forward drawdown is more than 2x the idea's dev drawdown.
The paper book then applies, to promoted ideas only: size cap 1 lot equivalent, one open position per idea, a portfolio cap on simultaneous
positions, and a daily loss limit (a day that loses more than the limit pauses new entries on the next trading day)."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import daily_forward as df_  # noqa: E402
import loop_config as cfg  # noqa: E402
import loop_stats as ls  # noqa: E402
import registry as reg  # noqa: E402
import rule_engine as rules  # noqa: E402
import forced_trader_ideas as fi  # noqa: E402


# ----------------------------------------------------------------------------------------------- forward statistics
def idea_rows(log: pd.DataFrame, idea_id: str, since=None, until=None) -> pd.DataFrame:
    r = log[log["idea_id"] == idea_id]
    if since is not None:
        r = r[r["signal_date"] > pd.Timestamp(since)]
    if until is not None:
        r = r[r["signal_date"] <= pd.Timestamp(until)]
    return r.sort_values(["exit_date", "signal_date"]).reset_index(drop=True)


def forward_stats(rows: pd.DataFrame, cost: float, with_null: bool = True) -> dict:
    """Numbers on forward days only: days, trades, mean net per trade, bootstrap p, random-entry null p, drawdown, last-40-days net."""
    trig = rows[rows["triggered"]]
    net = trig["net"].values.astype(float)
    st = {"days": int(len(rows)), "trades": int(len(trig)), "mean_net": float(net.mean()) if len(net) else float("nan"),
          "total_net": float(net.sum()), "boot_p": fi.bootstrap_p(net) if len(net) else 1.0, "null_p": 1.0,
          "drawdown": ls.max_drawdown(rows["net"].values.astype(float)),
          "last_window_net": float(rows["net"].tail(cfg.RETIRE_WINDOW).sum()), "last_window_days": int(min(len(rows), cfg.RETIRE_WINDOW))}
    if with_null and len(trig):
        t = fi._trades(0, "fwd", trig["entry_date"].values, trig["direction"].values, trig["gross_long"].values, np.ones(len(trig), int),
                       {1: rows["gross_long"].values.astype(float)}, (rows["signal_date"].min().date(), rows["signal_date"].max().date()))
        st["null_p"] = fi.null_p(t, cost)[0]
    return st


def promotion_checks(st: dict) -> dict:
    """Pure comparison so the edge cases (exactly 60 days, mean exactly 0, p exactly 0.05) are testable."""
    return {"days>=60": st["days"] >= cfg.FWD_MIN_DAYS, "trades>=20": st["trades"] >= cfg.FWD_MIN_TRADES,
            "net_mean>0": bool(st["trades"] > 0 and st["mean_net"] > 0), "boot_p<0.05": st["boot_p"] < cfg.FWD_ALPHA,
            "null_p<0.05": st["null_p"] < cfg.FWD_ALPHA}


def retire_checks(st: dict, dev_dd) -> dict:
    """True under `retire_*` means: retire. A rule that cannot be evaluated (too few days, no dev drawdown) never fires."""
    roll = st["last_window_days"] >= cfg.RETIRE_WINDOW and st["last_window_net"] < 0
    dd = dev_dd is not None and st["drawdown"] > cfg.RETIRE_DD_MULT * dev_dd
    return {"retire_rolling40": bool(roll), "retire_drawdown": bool(dd)}


def decide(idea: dict, log: pd.DataFrame, asof: date) -> dict:
    """What should happen to one idea today. Returns {action: promote|retire|none, stats, checks, reason}."""
    i = idea["id"]
    if idea["status"] == "forward":
        rows = idea_rows(log, i, idea["forward_since"], asof)
        st = forward_stats(rows, idea["cost"])
        ch = promotion_checks(st)
        return {"id": i, "action": "promote" if all(ch.values()) else "none", "stats": st, "checks": ch,
                "reason": "all forward checks passed" if all(ch.values()) else "not yet: " + ", ".join(k for k, v in ch.items() if not v)}
    if idea["status"] == "promoted":
        rows = idea_rows(log, i, idea["forward_since"], asof)
        st = forward_stats(rows, idea["cost"], with_null=False)
        ch = retire_checks(st, idea.get("dev_max_drawdown"))
        why = [f"last {cfg.RETIRE_WINDOW} days net {st['last_window_net']:+.4f} < 0" if ch["retire_rolling40"] else "",
               f"forward drawdown {st['drawdown']:.4f} > {cfg.RETIRE_DD_MULT:g} x dev drawdown {idea.get('dev_max_drawdown')}" if ch["retire_drawdown"] else ""]
        return {"id": i, "action": "retire" if any(ch.values()) else "none", "stats": st, "checks": ch, "reason": "; ".join(x for x in why if x) or "still inside limits"}
    return {"id": i, "action": "none", "stats": {}, "checks": {}, "reason": f"status {idea['status']}"}


# ----------------------------------------------------------------------------------------------- the paper book
def _span(entry, exit_):
    """Days a position occupies: [entry, exit); a same-day trade occupies its own day."""
    return (entry, exit_ if exit_ > entry else entry + pd.Timedelta(days=1))


def build_book(trades: pd.DataFrame, calendar, ideas: dict | None = None, lot_rs=cfg.LOT_NOTIONAL_RS, size_cap=cfg.SIZE_CAP_LOTS,
               loss_limit=cfg.DAILY_LOSS_LIMIT_RS, cap=cfg.PORTFOLIO_CAP) -> pd.DataFrame:
    """Apply the filters to the triggered trades of promoted ideas, in entry order. One row per trade with a status:
    taken | skipped_overlap (that idea already has a position) | skipped_portfolio_cap | skipped_loss_pause.
    size: the lots an idea asks for (default 1) are cut to size_cap. P&L = net return x lots x lot_rs. Paper only."""
    cols = ["idea_id", "signal_date", "entry_date", "exit_date", "status", "lots", "net", "pnl_rs"]
    if trades.empty:
        return pd.DataFrame(columns=cols)
    cal = sorted(pd.Timestamp(x) for x in set(calendar))
    t = trades.sort_values(["entry_date", "signal_date", "idea_id"]).reset_index(drop=True)
    taken: list = []  # (idea, span_start, span_end, exit_date, pnl)
    rows = []
    for e_date, grp in t.groupby("entry_date", sort=True):
        prev = [c for c in cal if c < e_date]
        paused = False
        if prev:
            day_pnl = sum(x[4] for x in taken if x[3] == prev[-1])
            paused = day_pnl < -loss_limit
        for r in grp.itertuples():
            lots = min((ideas or {}).get(r.idea_id, 1), size_cap)
            s, e = _span(r.entry_date, r.exit_date)
            if paused:
                status = "skipped_loss_pause"
            elif any(x[0] == r.idea_id and x[1] < e and s < x[2] for x in taken):
                status = "skipped_overlap"
            elif sum(1 for x in taken if x[1] < e and s < x[2]) >= cap:
                status = "skipped_portfolio_cap"
            else:
                status = "taken"
            pnl = float(r.net) * lots * lot_rs if status == "taken" else 0.0
            if status == "taken":
                taken.append((r.idea_id, s, e, r.exit_date, pnl))
            rows.append({"idea_id": r.idea_id, "signal_date": r.signal_date, "entry_date": r.entry_date, "exit_date": r.exit_date, "status": status,
                         "lots": lots if status == "taken" else 0, "net": float(r.net), "pnl_rs": pnl})
    return pd.DataFrame(rows, columns=cols)


def book_for(registry_rows: list, log: pd.DataFrame, asof: date | None = None) -> pd.DataFrame:
    """Triggered trades of promoted (and later retired) ideas, only from after their promotion day and up to their retirement day."""
    parts = []
    for r in registry_rows:
        if not r.get("promoted_on"):
            continue
        rows = idea_rows(log, r["id"], r["promoted_on"], r.get("retired_on") or asof)
        parts.append(rows[rows["triggered"]][["idea_id", "signal_date", "entry_date", "exit_date", "net"]])
    trades = pd.concat(parts) if parts else pd.DataFrame(columns=["idea_id", "signal_date", "entry_date", "exit_date", "net"])
    cal = set(log["signal_date"]) | set(log["exit_date"]) if len(log) else set()
    return build_book(trades, cal)


# ----------------------------------------------------------------------------------------------- run
def run(asof: date, apply: bool = False, paths=None) -> dict:
    p = paths or cfg.PATHS
    bad = reg.problems(p) + df_.check_log(p.forward_log)
    if bad:
        raise SystemExit("REFUSED: " + "; ".join(bad))
    log = df_.read_log(p.forward_log)
    decisions = [decide(r, log, asof) for r in reg.load(p) if r["status"] in ("forward", "promoted")]
    for d in sorted(decisions, key=lambda x: x["action"] != "retire"):  # retirements first
        if not apply or d["action"] == "none":
            continue
        if d["action"] == "promote":
            reg.set_status(d["id"], "promoted", "forward checks passed: " + str({k: round(v, 5) if isinstance(v, float) else v for k, v in d["stats"].items()}),
                           p, asof, promoted_on=str(asof))
        else:
            reg.set_status(d["id"], "retired", d["reason"], p, asof, retired_on=str(asof), retire_reason=d["reason"])
    book = book_for(reg.load(p), log, asof)
    if apply:
        p.results.mkdir(parents=True, exist_ok=True)
        book.to_csv(p.results / "paper_book.csv", index=False)
    return {"asof": str(asof), "applied": apply, "decisions": decisions, "book_rows": int(len(book)), "book_pnl_rs": float(book["pnl_rs"].sum()) if len(book) else 0.0}


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--apply", action="store_true")
    a.add_argument("--asof", help="default: today")
    a = a.parse_args()
    out = run(date.fromisoformat(a.asof) if a.asof else date.today(), a.apply)
    for d in out["decisions"]:
        s = d["stats"]
        print(f"{d['id']}: {d['action'].upper():7s} days {s.get('days')} trades {s.get('trades')} - {d['reason']}")
    print(f"paper book: {out['book_rows']} rows, P&L Rs {out['book_pnl_rs']:,.0f} (assumed lot value Rs {cfg.LOT_NOTIONAL_RS:,}); " + ("changes written" if a.apply else "nothing written (use --apply)"))


if __name__ == "__main__":
    main()
