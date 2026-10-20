"""Task 12 (B7-01): the crowd-positioning rule on Binance USDT-M perpetuals, rules exactly as in docs/ideas/IDEAS_BATCH7_CRYPTO_CROWD_2026-10-20.md.
Readings of ambiguous points are fixed in research/RESULTS.md ("Planned (pre-registered 2026-10-20 ...").

Pipeline: parsed 5-minute metrics files -> the row stamped 23:50:00 of each day -> x = ln(ratio) -> z over the previous 90 available values (min 60)
-> signal at |z| >= threshold (crowd long -> SHORT, crowd short -> LONG) -> enter at the OPEN of day D+1, exit at the OPEN of day D+2 -> net of 0.12% cost.
Dev data only: 2025-12-31 is the last date any function here accepts. Nothing here reads the hidden holdout or places orders.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ideas"))
import forced_trader_ideas as fi  # noqa: E402  (bootstrap_p, null_p, halves, Trades; read-only reuse)

DATA = HERE.parent / "data" / "crypto"
LAST_DEV = date(2025, 12, 31)
FIRST_HOLDOUT = datetime(2026, 1, 1)

COST = 0.0012  # 0.12% of notional per round trip = 0.05% fee per side + 0.02% slippage (pre-registered)
ALPHA = 0.05 / 17  # trial 17 overall
THRESHOLD, WINDOW, MIN_HIST = 1.5, 90, 60
MIN_TRADES = 100
BLOCK, N_BOOT, N_NULL, SEED = 5, 10_000, 10_000, 20261018
EPS = 1e-12  # float tolerance for "exactly at the threshold"
SIGNAL_TIME = "23:50:00"
STAMPS_PER_DAY = 288


# ----------------------------------------------------------------------------------------------- metrics files
def clean_day(df: pd.DataFrame) -> tuple:
    """Collapse rows that share one create_time to the FIRST of them. Returns (clean frame sorted by time, qa dict)."""
    n_raw = len(df)
    ts = pd.to_datetime(df["create_time"])
    df = df.assign(create_time=ts)
    dup = df["create_time"].duplicated(keep="first")
    first = df[~dup]
    cols = [c for c in df.columns if c != "create_time"]
    # a duplicate that differs from the row it duplicates in any value
    merged = df[dup].merge(first, on="create_time", suffixes=("", "_first"))
    conflicts = 0
    for _, r in merged.iterrows():
        for c in cols:
            a, b = r[c], r[c + "_first"]
            if not (a == b or (pd.isna(a) and pd.isna(b))):
                conflicts += 1
                break
    clean = first.sort_values("create_time").reset_index(drop=True)
    return clean, {"raw_rows": n_raw, "unique_rows": len(clean), "dup_rows": int(dup.sum()), "dup_conflicts": conflicts}


def signal_row(clean: pd.DataFrame, day: date, col: str, hms: str = SIGNAL_TIME):
    """The value of `col` in the row stamped exactly `hms` on `day`, or None if that row is missing or the value is not a positive finite number."""
    stamp = pd.Timestamp(f"{day.isoformat()} {hms}")
    rows = clean[clean["create_time"] == stamp]
    if rows.empty:
        return None, "no_2350_row"
    v = rows.iloc[0][col]
    if v is None or not np.isfinite(float(v)) or float(v) <= 0:
        return None, "bad_ratio"
    return float(v), None


def day_qa(clean: pd.DataFrame, day: date) -> dict:
    """Time-zone / gap checks for one day: stamps must lie on `day` at 5-minute steps from 00:00:00 to 23:55:00."""
    t = clean["create_time"]
    on_day = (t.dt.date == day)
    on_grid = ((t.dt.minute % 5 == 0) & (t.dt.second == 0))
    return {"n_unique": len(clean), "off_day": int((~on_day).sum()), "off_grid": int((~on_grid).sum()),
            "first": str(t.min().time()) if len(t) else None, "last": str(t.max().time()) if len(t) else None,
            "full_day": bool(len(clean) == STAMPS_PER_DAY and on_day.all() and on_grid.all())}


def day_of(path: Path) -> date:
    return date.fromisoformat(path.stem[-10:])  # ...-metrics-YYYY-MM-DD


def load_signal_columns(sym: str, cols=("count_long_short_ratio", "count_toptrader_long_short_ratio"), base: Path | None = None) -> tuple:
    """Read every parsed daily metrics file of `sym` (dev only). Returns (frame indexed by date with one column per `cols` holding the 23:50 value or NaN,
    reasons frame with the skip reason per date and column, qa DataFrame one row per file)."""
    base = base or DATA / "parsed" / "metrics" / sym
    files = sorted(base.glob(f"{sym}-metrics-*.csv"))
    vals, why, qa = {}, {}, []
    for f in files:
        d = day_of(f)
        if d > LAST_DEV:
            raise RuntimeError(f"holdout file on disk: {f.name}")
        clean, q = clean_day(pd.read_csv(f))
        q.update(day_qa(clean, d))
        q["date"] = d
        qa.append(q)
        vals[d], why[d] = {}, {}
        for c in cols:
            v, r = signal_row(clean, d, c)
            vals[d][c], why[d][c] = (np.nan if v is None else v), r
    x, w = pd.DataFrame.from_dict(vals, orient="index"), pd.DataFrame.from_dict(why, orient="index")
    x.index, w.index = pd.to_datetime(x.index), pd.to_datetime(w.index)
    return x, w, pd.DataFrame(qa)


# ----------------------------------------------------------------------------------------------- klines
def read_klines(path: Path) -> pd.DataFrame:
    """Binance kline CSV (with or without a header row) -> frame indexed by open time (UTC, naive) with an `open` column."""
    raw = pd.read_csv(path, header=None)
    if not str(raw.iloc[0, 0]).lstrip("-").isdigit():
        raw = raw.iloc[1:]
    t = pd.to_numeric(raw[0]).astype("int64")
    unit = "us" if t.max() > 1e14 else "ms"
    out = pd.DataFrame({"open": pd.to_numeric(raw[1]).values}, index=pd.to_datetime(t.values, unit=unit))
    return out


def load_opens(sym: str, kind: str = "klines1d", base: Path | None = None) -> pd.Series:
    """Open price by open time for every monthly kline file of `sym` (dev only; raises if any bar is dated 2026-01-01 or later)."""
    base = base or DATA / "parsed" / kind / sym
    parts = [read_klines(f) for f in sorted(base.glob("*.csv"))]
    s = pd.concat(parts)["open"]
    s = s[~s.index.duplicated(keep="first")].sort_index()
    if len(s) and s.index.max() >= FIRST_HOLDOUT:
        raise RuntimeError("kline data at or after 2026-01-01 present")
    return s


# ----------------------------------------------------------------------------------------------- signal
def zscores(x: pd.Series, window: int = WINDOW, minimum: int = MIN_HIST) -> pd.DataFrame:
    """z for every date in `x` (index = dates, NaN = no x that day). For date D: the last `window` NON-missing x values dated strictly BEFORE D,
    their mean and SAMPLE std (ddof 1). Fewer than `minimum` values -> status 'lt60_history'; std 0 -> 'zero_sd'. Rows for dates with no x are 'no_x'."""
    idx = list(x.index)
    arr = x.to_numpy(float)
    z = np.full(len(arr), np.nan)
    status = [""] * len(arr)
    span = np.full(len(arr), np.nan)
    hist: list = []  # (position, value) of valid values seen so far, in order
    for i, v in enumerate(arr):
        if np.isfinite(v):
            prior = hist[-window:]
            if len(prior) < minimum:
                status[i] = "lt60_history"
            else:
                vals = np.array([p[1] for p in prior])
                sd = vals.std(ddof=1)
                if sd == 0 or not np.isfinite(sd):
                    status[i] = "zero_sd"
                else:
                    z[i] = (v - vals.mean()) / sd
                    status[i] = "ok"
                    span[i] = (idx[i] - idx[prior[0][0]]).days
            hist.append((i, v))
        else:
            status[i] = "no_x"
    return pd.DataFrame({"z": z, "status": status, "span_days": span}, index=x.index)


def direction(z: float, thr: float = THRESHOLD) -> int:
    """+1 long, -1 short, 0 flat. Crowd heavily long (z high) -> SHORT; crowd heavily short (z low) -> LONG."""
    if not np.isfinite(z):
        return 0
    if z >= thr - EPS:
        return -1
    if z <= -thr + EPS:
        return 1
    return 0


@dataclass
class Run:
    trades: pd.DataFrame  # one row per trade: signal_date, entry, exit, direction, z, gross (LONG return exit/entry-1), net
    days: pd.DataFrame  # one row per calendar day: status (traded / flat / skip reason)
    pool: np.ndarray  # long gross returns of every eligible day (z defined and both prices present), for the random-entry null
    window: tuple


def build_trades(z: pd.DataFrame, opens: pd.Series, first_day: date, hold: timedelta = timedelta(days=1), thr: float = THRESHOLD, cost: float = COST,
                 sign: int = 1, last_day: date = LAST_DEV) -> Run:
    """z: output of zscores (index = dates). opens: open price indexed by bar open time. For a signal on date D: entry = open at D+1 00:00, exit = open at
    entry + hold. Missing price or an exit after `last_day` -> 'no_price'. A signal whose entry is before the previous trade's exit -> 'overlap'.
    `sign` = -1 gives the opposite (follow-the-crowd) direction. Every calendar day first_day..last_day gets a status row."""
    rows, days, pool = [], [], []
    last_exit = None
    all_days = pd.date_range(first_day, last_day, freq="D")
    zz = z.reindex(all_days)
    for d in all_days:
        st = zz.loc[d, "status"]
        if not isinstance(st, str) or st == "":
            days.append((d.date(), "no_file"))
            continue
        if st != "ok":
            days.append((d.date(), {"no_x": "no_x"}.get(st, st)))
            continue
        entry_ts = d + timedelta(days=1)
        exit_ts = entry_ts + hold
        e, x = opens.get(entry_ts, np.nan), opens.get(exit_ts, np.nan)
        if exit_ts.date() > last_day or not (np.isfinite(e) and np.isfinite(x)):
            days.append((d.date(), "no_price"))
            continue
        gross = x / e - 1.0
        pool.append(gross)
        dr = sign * direction(float(zz.loc[d, "z"]), thr)
        if dr == 0:
            days.append((d.date(), "flat"))
            continue
        if last_exit is not None and entry_ts < last_exit:
            days.append((d.date(), "overlap"))
            continue
        last_exit = exit_ts
        days.append((d.date(), "traded"))
        rows.append({"signal_date": d, "entry": entry_ts, "exit": exit_ts, "direction": dr, "z": float(zz.loc[d, "z"]), "gross": gross,
                     "net": dr * gross - cost, "net_zero_cost": dr * gross})
    tr = pd.DataFrame(rows, columns=["signal_date", "entry", "exit", "direction", "z", "gross", "net", "net_zero_cost"])
    return Run(tr, pd.DataFrame(days, columns=["date", "status"]), np.array(pool, float), (all_days[0].date(), last_day))


# ----------------------------------------------------------------------------------------------- statistics
def max_drawdown(r: np.ndarray) -> float:
    """Largest peak-to-trough fall of the cumulative sum of per-trade returns, starting from 0 (returned as a positive number, 0 if none)."""
    c = np.concatenate([[0.0], np.cumsum(np.asarray(r, float))])
    return float((np.maximum.accumulate(c) - c).max())


def as_trades(run: Run, idea: int = 701, name: str = "B7-01") -> "fi.Trades":
    t = run.trades
    return fi.Trades(idea=idea, name=name, entry_date=t["entry"].to_numpy("datetime64[D]"), direction=t["direction"].to_numpy(int),
                     gross=t["gross"].to_numpy(float), hold=np.zeros(len(t), int), cand={0: run.pool}, window=run.window)


def stats(run: Run, cost: float = COST, with_null: bool = True) -> dict:
    t = run.trades
    n = len(t)
    net = (t["direction"] * t["gross"] - cost).to_numpy(float)
    zero = (t["direction"] * t["gross"]).to_numpy(float)
    out = {"n_trades": n, "n_long": int((t["direction"] > 0).sum()), "n_short": int((t["direction"] < 0).sum()),
           "mean_net": float(net.mean()) if n else float("nan"), "mean_zero_cost": float(zero.mean()) if n else float("nan"),
           "median_net": float(np.median(net)) if n else float("nan"), "win_rate": float((net > 0).mean()) if n else float("nan"),
           "boot_p": fi.bootstrap_p(net, BLOCK, N_BOOT, SEED), "boot_p_zero_cost": fi.bootstrap_p(zero, BLOCK, N_BOOT, SEED),
           "worst_trade": float(net.min()) if n else float("nan"), "best_trade": float(net.max()) if n else float("nan"),
           "max_drawdown": max_drawdown(net), "total_net": float(net.sum())}
    if n:
        w = t.loc[net.argmin()]
        out["worst_trade_info"] = {"signal_date": str(w["signal_date"].date()), "direction": int(w["direction"]), "gross_long_return": float(w["gross"])}
    if with_null and n:
        tr = as_trades(run)
        out["null_p"], out["null_mean"], out["null_q95"] = fi.null_p(tr, cost, N_NULL, SEED)
        out["null_p_zero_cost"] = fi.null_p(tr, 0.0, N_NULL, SEED)[0]
        out["pool_days"] = int(len(run.pool))
    h = fi.halves(as_trades(run), cost) if n else {}
    out.update(h)
    out["halves_zero_cost"] = {k: v for k, v in (fi.halves(as_trades(run), 0.0).items() if n else []) if k.endswith("_mean")}
    return out


def by_year(run: Run, cost: float = COST) -> list:
    t = run.trades
    if t.empty:
        return []
    y = t["entry"].dt.year
    rows = []
    for yr in sorted(y.unique()):
        s = t[y == yr]
        net = (s["direction"] * s["gross"] - cost).to_numpy(float)
        rows.append({"year": int(yr), "n": len(s), "n_long": int((s["direction"] > 0).sum()), "n_short": int((s["direction"] < 0).sum()),
                     "mean_net": float(net.mean()), "mean_zero_cost": float((s["direction"] * s["gross"]).mean()), "total_net": float(net.sum()),
                     "worst": float(net.min()), "max_drawdown_in_year": max_drawdown(net)})
    return rows


def skip_counts(run: Run) -> dict:
    return {k: int(v) for k, v in run.days["status"].value_counts().items()}
