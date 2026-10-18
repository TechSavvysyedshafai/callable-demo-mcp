"""Daily paper-forward job. Run AFTER the market closes. For every idea with status `forward` it settles, into an append-only csv
(forward_log.csv), every start day whose trade has now finished: what the rule's signal was (using only rows up to that day), the
direction, the gross return, the batch cost and the net paper P&L (as a fraction of notional). Nothing is ever re-tuned or re-fit.

  python daily_forward.py                          # live: today (India time), data from Upstox via research/upstox/upstox_api.py
  python daily_forward.py --asof 2026-11-03        # live, a given past day (catch-up: only days after each idea's forward_since are logged)
  python daily_forward.py --dry-run --asof 2026-03-02 --ideas B2-01   # plumbing test on the dev CSVs, pretending today is that day

One log row = one eligible start day of one idea (triggered or not), keyed by (idea_id, signal_date). Re-running a day never adds a row twice.
Only start days AFTER the idea's forward_since are logged, so the dev period can never leak into the forward record.
A trade that is still open (exit after `asof`) is not logged yet; it appears on the day it finishes.
The job places no orders and keeps no secrets: the Upstox token is read from the environment by the existing adapter and never printed."""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import loop_config as cfg  # noqa: E402
import registry as reg  # noqa: E402
import rule_engine as rules  # noqa: E402
import forced_trader_ideas as fi  # noqa: E402

LOG_COLS = ["idea_id", "signal_date", "entry_date", "exit_date", "triggered", "direction", "gross_long", "cost", "net", "batch", "logged_on"]


def read_log(path: Path) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame(columns=LOG_COLS)
    d = pd.read_csv(path, parse_dates=["signal_date", "entry_date", "exit_date"])
    d["triggered"] = d["triggered"].astype(bool)
    return d


def check_log(path: Path) -> list:
    """Problems in the log: duplicate keys, or a trade that exits before it enters."""
    d = read_log(path)
    out = []
    if d.duplicated(["idea_id", "signal_date"]).any():
        out.append("duplicate (idea, signal day) rows")
    if (d["exit_date"] < d["entry_date"]).any():
        out.append("a trade exits before it enters")
    return out


def settle(idea: dict, daily, vix, m5, asof: date, logged: set) -> pd.DataFrame:
    """New log rows for one idea: eligible start days after forward_since, finished by asof, not logged yet.
    Uses only data up to asof, and every feature of a start day only looks at rows up to that day (tested)."""
    since = pd.Timestamp(idea["forward_since"])
    cut = pd.Timestamp(asof)
    d = daily[daily["date"] <= cut] if daily is not None else None
    v = vix[vix["date"] <= cut] if vix is not None else None
    m = m5[m5["date"] < cut + pd.Timedelta(days=1)] if m5 is not None else None
    sc = rules.scan(idea["rule"], d, v, m)
    sc = sc[(sc["signal_date"] > since) & (sc["exit_date"] <= cut)]
    sc = sc[[(idea["id"], pd.Timestamp(s)) not in logged for s in sc["signal_date"]]].copy()
    if sc.empty:
        return pd.DataFrame(columns=LOG_COLS)
    sc["net"] = sc["direction"] * sc["gross"] - idea["cost"] * sc["triggered"]
    out = pd.DataFrame({"idea_id": idea["id"], "signal_date": sc["signal_date"], "entry_date": sc["entry_date"], "exit_date": sc["exit_date"],
                        "triggered": sc["triggered"], "direction": sc["direction"], "gross_long": sc["gross"], "cost": idea["cost"], "net": sc["net"],
                        "batch": idea["batch"], "logged_on": str(asof)})
    return out[LOG_COLS]


def run_day(asof: date, ideas: list, data: tuple, log_path: Path) -> dict:
    """Core, no network. ideas: registry rows to treat as forward. Appends only rows not yet in the log."""
    old = read_log(log_path)
    logged = {(r.idea_id, pd.Timestamp(r.signal_date)) for r in old.itertuples()}
    d, v, m = data
    new = []
    for idea in ideas:
        if not idea.get("forward_since"):
            raise ValueError(f"{idea['id']} has no forward_since date")
        new.append(settle(idea, d, v, m, asof, logged))
    new = pd.concat([x for x in new if len(x)] or [pd.DataFrame(columns=LOG_COLS)])
    if len(new):
        new = new.sort_values(["signal_date", "idea_id"])
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        new.assign(signal_date=new["signal_date"].dt.date, entry_date=new["entry_date"].dt.date, exit_date=new["exit_date"].dt.date).to_csv(
            log_path, mode="a", header=not Path(log_path).exists(), index=False)
    return {"asof": str(asof), "ideas": [i["id"] for i in ideas], "new_rows": int(len(new)), "new_triggered": int(new["triggered"].sum()) if len(new) else 0,
            "rows_before": int(len(old))}


# ----------------------------------------------------------------------------------------------- data
def dry_data(dev_dir: Path, asof: date, ideas: list) -> tuple:
    """Dev CSVs cut at the simulated 'today': the job cannot see anything later."""
    if "holdout" in str(dev_dir).lower():
        raise SystemExit("REFUSED: dry runs read the dev folder only")
    need = {k: any(rules.needs(i["rule"])[k] for i in ideas) for k in ("daily", "vix", "m5")}
    f = {k: Path(dev_dir) / v for k, v in cfg.DEV_FILES.items()}
    miss = [str(f[k]) for k in need if need[k] and not f[k].exists()]
    if miss:
        raise SystemExit(f"REFUSED: dev data not found {miss} (see research/upstox/fetch_upstox.py)")
    cut = pd.Timestamp(asof)
    d = fi.load_daily(f["daily"]) if need["daily"] else None
    v = fi.load_vix(f["vix"]) if need["vix"] else None
    m = fi.load_5min(f["m5"]) if need["m5"] else None
    return (d[d["date"] <= cut] if d is not None else None, v[v["date"] <= cut] if v is not None else None,
            m[m["date"] < cut + pd.Timedelta(days=1)] if m is not None else None)


def live_data(asof: date, ideas: list) -> tuple:
    """Daily / 5-minute bars from Upstox through the existing adapter. Fetches only from a little before the earliest forward_since
    (enough history for the rules' features), never the whole past."""
    sys.path.insert(0, str(cfg.RESEARCH / "upstox"))
    import upstox_api as u  # reads the token from the environment; never printed here
    ns = [rules.needs(i["rule"]) for i in ideas]
    back = max(n["lookback_rows"] + n["max_exit_day"] for n in ns) * 2 + 14  # calendar days, generous
    start = min(date.fromisoformat(i["forward_since"]) for i in ideas) - timedelta(days=back)
    d = v = m = None
    if any(n["daily"] for n in ns):
        d = u.historical(u.NIFTY, "days", 1, start, asof)
        d["date"] = d["date"].dt.normalize()
    if any(n["vix"] for n in ns):
        v = u.historical(u.INDIA_VIX, "days", 1, start, asof)
        v["date"] = v["date"].dt.normalize()
    if any(n["m5"] for n in ns):
        m = u.historical(u.NIFTY, "minutes", 5, start, asof)
    return d, v, m


def ist_now() -> datetime:
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Kolkata"))


def after_close_ist(asof: date, now: datetime | None = None) -> bool:
    """Live runs for the current Indian day wait until 15:45 so the day's last bar is final."""
    now = now or ist_now()
    if asof < now.date():
        return True
    return asof == now.date() and now.hour * 60 + now.minute >= cfg.CLOSE_IST_MINUTES


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--asof", help="day to settle through (default: today, India time)")
    a.add_argument("--dry-run", action="store_true", help="use the dev CSVs, write to a scratch folder, never the real log")
    a.add_argument("--ideas", help="dry run only: comma list of registered DSL idea ids to treat as forward")
    a.add_argument("--forward-since", help="dry run only: pretend the ideas became forward on this date (default asof - 45 days)")
    a.add_argument("--dev-dir", help="dry run only: folder with the dev CSVs")
    a.add_argument("--out-dir", help="dry run only: where to write the scratch log")
    a = a.parse_args()
    p = cfg.Paths()
    if a.dry_run:
        if not a.asof:
            sys.exit("--dry-run needs --asof (the simulated today)")
        asof = date.fromisoformat(a.asof)
        ids = [x for x in (a.ideas or "").split(",") if x]
        if not ids:
            sys.exit("--dry-run needs --ideas ID[,ID] (registered ideas with a daily/intraday rule)")
        fs = a.forward_since or str(asof - timedelta(days=45))
        ideas = [dict(reg.get(i, p), forward_since=fs) for i in ids]
        for i in ideas:
            if i["rule"].get("kind") not in ("daily", "intraday"):
                sys.exit(f"REFUSED: {i['id']} has no machine-readable daily/intraday rule (Batch 1 ideas are closed)")
        out = Path(a.out_dir or tempfile.mkdtemp(prefix="loop_dryrun_"))
        log = out / "forward_log_dryrun.csv"
        if log.resolve() == p.forward_log.resolve():
            sys.exit("REFUSED: a dry run never writes the real forward log")
        data = dry_data(Path(a.dev_dir or p.dev_dir), asof, ideas)
        print("DRY RUN (dev CSVs, simulated today):", run_day(asof, ideas, data, log), "->", log)
        return
    asof = date.fromisoformat(a.asof) if a.asof else ist_now().date()
    if not after_close_ist(asof):
        sys.exit("The market has not closed yet in India (wait until 15:45) - nothing recorded.")
    bad = reg.problems(p)
    if bad:
        sys.exit("REFUSED: " + "; ".join(bad))
    ideas = reg.by_status("forward", p)
    if not ideas:
        print("No idea has status forward - nothing to do.")
        return
    summary = run_day(asof, ideas, live_data(asof, ideas), p.forward_log)
    bad = check_log(p.forward_log)
    print(summary, "LOG PROBLEMS: " + "; ".join(bad) if bad else "")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
