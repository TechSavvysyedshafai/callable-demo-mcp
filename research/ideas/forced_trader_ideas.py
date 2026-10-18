"""Task 5: the 10 pre-registered "forced trader" ideas (docs/ideas/IDEAS_BATCH1_2026-10-18.md), rules exactly as written.

Every idea function returns a `Trades` object: the real trades plus, for the random-entry null, the gross return of
EVERY possible start of the same template (`cand`). Readings of ambiguous rules are fixed in research/RESULTS.md
("Planned (pre-registered 2026-10-18, branch claude/employee-ideas ...").

Conventions: a trade's return = direction x (exit / entry - 1) - COST. Index levels stand in for futures (no basis/roll).
A 5-minute bar labelled T opens at T, so "price at T" is the OPEN of bar T and "close of bar T" is the price at T + 5 min.
Dev data only (research/data). Nothing here reads the hidden holdout or places orders.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

COST = 0.001  # 0.10% of notional per round trip (pre-registered)
ALPHA = 0.005  # Bonferroni: 0.05 / 10
MIN_TRADES = 60
BLOCK, N_BOOT, N_NULL, SEED = 5, 10_000, 10_000, 20261018
EPS = 1e-12  # float tolerance for the "exactly at the threshold" cases
THU_UNTIL, TUE_FROM = date(2025, 8, 28), date(2025, 9, 2)
# Diwali Muhurat sessions (one evening hour on a day the regular market is closed). Rows dated Sat/Sun are special sessions too.
# 2021-11-04 (Thu) confirmed as holiday + Muhurat by NSE holiday lists; 2024-11-01 and 2025-10-21 show 12 five-minute bars in the data;
# 2018-11-07 and 2022-10-24 are from memory (not on an expiry weekday, so they cannot change the expiry list).
MUHURAT = {date(2018, 11, 7), date(2021, 11, 4), date(2022, 10, 24), date(2024, 11, 1), date(2025, 10, 21)}


@dataclass
class Trades:
    idea: int
    name: str
    entry_date: np.ndarray  # datetime64[D], one per trade
    direction: np.ndarray  # +1 / -1
    gross: np.ndarray  # LONG gross return of each trade: exit / entry - 1
    hold: np.ndarray  # template key per trade (rows held, or 0 for same-bar templates)
    cand: dict  # hold key -> gross long returns of every possible start of that template
    window: tuple  # (first date, last date) of the data used (for the halves)
    skipped: int = 0
    notes: dict = field(default_factory=dict)

    def net(self, cost: float = COST) -> np.ndarray:
        return self.direction * self.gross - cost


# ----------------------------------------------------------------------------------------------- data
def load_daily(path: Path | None = None) -> pd.DataFrame:
    d = pd.read_csv(path or DATA / "nifty_day_dev.csv", parse_dates=["date"])
    d["date"] = d["date"].dt.normalize()
    return d.sort_values("date").reset_index(drop=True)


def load_vix(path: Path | None = None) -> pd.DataFrame:
    v = pd.read_csv(path or DATA / "india_vix_day.csv", parse_dates=["date"])
    v["date"] = v["date"].dt.normalize()
    return v.sort_values("date").reset_index(drop=True)


def load_5min(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or DATA / "nifty_5minute_dev.csv", parse_dates=["date"]).sort_values("date").reset_index(drop=True)


def bars_by_day(m: pd.DataFrame, times: tuple) -> pd.DataFrame:
    """One row per day with columns o_HHMM, c_HHMM for the wanted bar labels (NaN when a bar is missing)."""
    t = m["date"].dt.strftime("%H%M")
    sel = m[t.isin(times)].copy()
    sel["t"] = t[t.isin(times)]
    sel["day"] = sel["date"].dt.normalize()
    o = sel.pivot(index="day", columns="t", values="open").add_prefix("o_")
    c = sel.pivot(index="day", columns="t", values="close").add_prefix("c_")
    out = o.join(c, how="outer")
    for tt in times:
        for p in ("o_", "c_"):
            if p + tt not in out:
                out[p + tt] = np.nan
    return out.sort_index()


def _dates(d: pd.DataFrame) -> np.ndarray:
    return d["date"].values.astype("datetime64[D]")


def _window(d: pd.DataFrame) -> tuple:
    return (d["date"].iloc[0].date(), d["date"].iloc[-1].date())


def _cc(C: np.ndarray, h: int) -> np.ndarray:
    return C[h:] / C[:-h] - 1


def _trades(idea, name, dates, direction, gross, hold, cand, window, skipped=0, **notes) -> Trades:
    return Trades(idea, name, np.asarray(dates, "datetime64[D]"), np.asarray(direction, float), np.asarray(gross, float),
                  np.asarray(hold, int), cand, window, skipped, notes)


# ----------------------------------------------------------------------------------------------- the ideas
def idea1_sip(d: pd.DataFrame) -> Trades:
    """Long close of the 2nd-last trading day of a month to close of the 3rd trading day of the next month."""
    C, dt = d["close"].values, d["date"]
    ym = (dt.dt.year * 12 + dt.dt.month).values
    last_ym = ym[-1]
    ent, ext, dts = [], [], []
    for m in np.unique(ym):
        if m == last_ym:
            continue  # last month in the file is partial: its end is unknown
        rows = np.where(ym == m)[0]
        nxt = np.where(ym == m + 1)[0]  # months with no rows at all would be a data hole; none in this file
        if len(rows) < 2 or len(nxt) < 3:
            continue
        ent.append(rows[-2])
        ext.append(nxt[2])
        dts.append(dt.iloc[rows[-2]])
    ent, ext = np.array(ent, int), np.array(ext, int)
    hold = ext - ent
    cand = {int(h): _cc(C, int(h)) for h in np.unique(hold)}
    return _trades(1, "SIP and salary inflows", dts, np.ones(len(ent)), C[ext] / C[ent] - 1, hold, cand, _window(d))


def idea2_overnight(d: pd.DataFrame) -> Trades:
    """Long every close to the next row's open. (Trial = this leg. The intraday leg is reported separately.)"""
    O, C = d["open"].values, d["close"].values
    g = O[1:] / C[:-1] - 1
    return _trades(2, "Day traders squaring off (overnight leg)", _dates(d)[:-1], np.ones(len(g)), g, np.zeros(len(g), int), {0: g}, _window(d))


def idea2_intraday_info(d: pd.DataFrame) -> Trades:
    O, C = d["open"].values, d["close"].values
    g = C / O - 1
    return _trades(2, "Intraday leg (information only, not a trial)", _dates(d), np.ones(len(g)), g, np.zeros(len(g), int), {0: g}, _window(d))


def idea3_gap_fade(d: pd.DataFrame, gap: float = 0.007) -> Trades:
    """If |open / previous close - 1| > 0.7%, trade against the gap from open to close."""
    O, C = d["open"].values, d["close"].values
    gp = O[1:] / C[:-1] - 1
    og = C[1:] / O[1:] - 1  # open -> close of the gap day
    sel = np.abs(gp) > gap + EPS
    cand = {0: og}
    return _trades(3, "Gap chasers and stop-outs (fade the gap)", _dates(d)[1:][sel], -np.sign(gp[sel]), og[sel], np.zeros(sel.sum(), int), cand, _window(d))


def idea4_forced_sellers(d: pd.DataFrame, drop: float = 0.02) -> Trades:
    """After a close down 2% or more, long next open to next close."""
    O, C = d["open"].values, d["close"].values
    r = C[1:] / C[:-1] - 1  # r[k] = return of row k+1
    idx = np.where(r <= -drop + EPS)[0] + 1  # signal rows
    idx = idx[idx + 1 < len(d)]  # need a next row
    og = C / O - 1
    return _trades(4, "Forced sellers (margin calls)", _dates(d)[idx + 1], np.ones(len(idx)), og[idx + 1], np.zeros(len(idx), int), {0: og[1:]}, _window(d))


def idea5_vix_panic(d: pd.DataFrame, v: pd.DataFrame, rise: float = 0.15, hold: int = 3) -> Trades:
    """After India VIX rises 15%+ in a day, long NIFTY at that close, exit at the close 3 trading days later."""
    C = d["close"].values
    vr = v["close"].values[1:] / v["close"].values[:-1] - 1
    sig_dates = v["date"].values[1:][vr >= rise - EPS].astype("datetime64[D]")
    pos = {np.datetime64(x, "D"): i for i, x in enumerate(_dates(d))}
    ent, skipped = [], 0
    for s in sig_dates:
        i = pos.get(s)
        if i is None or i + hold >= len(d):
            skipped += 1  # signal date not a NIFTY row, or exit beyond the data
            continue
        ent.append(i)
    ent = np.array(ent, int)
    g = C[ent + hold] / C[ent] - 1
    # window of this idea = overlap of the VIX file and the daily file
    w = (max(_window(d)[0], v["date"].iloc[0].date()), min(_window(d)[1], v["date"].iloc[-1].date()))
    cand = {hold: _cc(C, hold)}
    return _trades(5, "Panic hedgers (VIX +15%)", _dates(d)[ent], np.ones(len(ent)), g, np.full(len(ent), hold), cand, w, skipped)


def idea6_closing(m: pd.DataFrame) -> Trades:
    """5-min: sign of open(15:15)/open(14:15) - 1; trade that direction from open of bar 15:15 to CLOSE of bar 15:25."""
    b = bars_by_day(m, ("1415", "1515", "1525"))
    ok = b[["o_1415", "o_1515", "c_1525"]].notna().all(axis=1)
    b2 = b[ok]
    r = b2["o_1515"].values / b2["o_1415"].values - 1
    g = b2["c_1525"].values / b2["o_1515"].values - 1
    sel = r != 0
    days = b2.index.values.astype("datetime64[D]")
    return _trades(6, "Closing-auction and index funds", days[sel], np.sign(r[sel]), g[sel], np.zeros(sel.sum(), int), {0: g},
                   (m["date"].iloc[0].date(), m["date"].iloc[-1].date()), skipped=int((~ok).sum()))


def idea7_morning(m: pd.DataFrame) -> Trades:
    """5-min: sign of the first-30-minute return (close of bar 09:40 / open of bar 09:15 - 1), trade it 09:45 -> 15:15 (open to open)."""
    b = bars_by_day(m, ("0915", "0940", "0945", "1515"))
    ok = b[["o_0915", "c_0940", "o_0945", "o_1515"]].notna().all(axis=1)
    b2 = b[ok]
    r = b2["c_0940"].values / b2["o_0915"].values - 1
    g = b2["o_1515"].values / b2["o_0945"].values - 1
    sel = r != 0
    days = b2.index.values.astype("datetime64[D]")
    return _trades(7, "Early-morning order flow", days[sel], np.sign(r[sel]), g[sel], np.zeros(sel.sum(), int), {0: g},
                   (m["date"].iloc[0].date(), m["date"].iloc[-1].date()), skipped=int((~ok).sum()))


def missing_weekdays_after(d: pd.DataFrame) -> np.ndarray:
    """For each row i < n-1: number of Mon-Fri dates strictly between row i and row i+1 that are not rows."""
    dd = _dates(d)
    return np.busday_count(dd[:-1] + np.timedelta64(1, "D"), dd[1:])


def idea8_preholiday(d: pd.DataFrame) -> Trades:
    """Long close of the last trading day before a market holiday (>=1 missing weekday) to the next row's open."""
    O, C = d["open"].values, d["close"].values
    miss = missing_weekdays_after(d)
    sel = miss >= 1
    g = O[1:] / C[:-1] - 1
    return _trades(8, "Pre-holiday risk-takers", _dates(d)[:-1][sel], np.ones(sel.sum()), g[sel], np.zeros(sel.sum(), int), {0: g}, _window(d),
                   holidays_found=int(sel.sum()))


def idea9_weekend(d: pd.DataFrame) -> Trades:
    """Long Friday close to Monday close (Friday date + 3 days must be a row)."""
    C, dd = d["close"].values, _dates(d)
    pos = {x: i for i, x in enumerate(dd)}
    ent, ext, skipped = [], [], 0
    for i, x in enumerate(dd):
        if pd.Timestamp(x).weekday() != 4:
            continue
        j = pos.get(x + np.timedelta64(3, "D"))
        if j is None:
            skipped += 1  # Friday or Monday closed (or the data has no Monday row): no trade
            continue
        ent.append(i)
        ext.append(j)
    ent, ext = np.array(ent, int), np.array(ext, int)
    g = C[ext] / C[ent] - 1
    return _trades(9, "Weekend risk reducers", dd[ent], np.ones(len(ent)), g, np.ones(len(ent), int), {1: _cc(C, 1)}, _window(d), skipped)


def expiry_rows(d: pd.DataFrame) -> np.ndarray:
    """Row index of each weekly-expiry day: Thursday up to 2025-08-28, Tuesday from 2025-09-02; if that weekday is not a
    trading row, the PREVIOUS trading row (exchange rule)."""
    dd_all = _dates(d)
    special = np.array([pd.Timestamp(x).weekday() >= 5 or pd.Timestamp(x).date() in MUHURAT for x in dd_all])
    reg = np.where(~special)[0]  # regular-session rows only: a Muhurat day is not an expiry day (real expiry moves earlier)
    dd = dd_all[reg]
    first, last = pd.Timestamp(dd[0]).date(), pd.Timestamp(dd[-1]).date()
    rows = set()
    cur = first
    while cur <= last:
        wd = cur.weekday()
        if (wd == 3 and cur <= THU_UNTIL) or (wd == 1 and cur >= TUE_FROM):
            k = np.searchsorted(dd, np.datetime64(cur, "D"), side="right") - 1  # last row on or before the weekday
            if k >= 0:
                rows.add(int(reg[k]))
        cur += timedelta(days=1)
    return np.array(sorted(rows), int)


def idea10_expiry(d: pd.DataFrame) -> Trades:
    """Trade expiry day open->close in the direction of the previous day's close-to-close return."""
    O, C = d["open"].values, d["close"].values
    er = expiry_rows(d)
    er = er[er >= 2]  # need close(t-1) and close(t-2)
    prev = C[er - 1] / C[er - 2] - 1
    sel = prev != 0
    og = C / O - 1
    er = er[sel]
    return _trades(10, "Weekly-expiry flows", _dates(d)[er], np.sign(prev[sel]), og[er], np.zeros(len(er), int), {0: og}, _window(d))


# ----------------------------------------------------------------------------------------------- statistics
def bootstrap_p(x: np.ndarray, block: int = BLOCK, n_boot: int = N_BOOT, seed: int = SEED) -> float:
    """One-sided p that the true mean is <= 0: moving-block bootstrap of chronological returns, centred on the sample mean."""
    x = np.asarray(x, float)
    m = len(x)
    if m == 0:
        return 1.0
    b = min(block, m)
    rng = np.random.default_rng(seed)
    k = int(np.ceil(m / b))
    starts = rng.integers(0, m - b + 1, size=(n_boot, k))
    idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(n_boot, -1)[:, :m]
    means = x[idx].mean(axis=1) - x.mean()
    return float((1 + np.sum(means >= x.mean() - 0.0)) / (n_boot + 1))


def null_p(t: Trades, cost: float = COST, n_draw: int = N_NULL, seed: int = SEED, chunk: int = 500) -> tuple:
    """Random-entry null: same number of trades per holding key drawn from every possible start of the same template,
    real directions assigned in random order, same cost. Returns (p, null mean, null 95th percentile)."""
    rng = np.random.default_rng(seed)
    n_tot = len(t.gross)
    if n_tot == 0:
        return 1.0, 0.0, 0.0
    obs = float(t.net(cost).mean())
    stat = np.zeros(n_draw)
    for key in np.unique(t.hold):
        mask = t.hold == key
        dirs = t.direction[mask]
        n_long, n_short = int((dirs > 0).sum()), int((dirs < 0).sum())
        n = n_long + n_short
        cand = t.cand[int(key)]
        M = len(cand)
        n = min(n, M)
        n_long = min(n_long, n)
        n_short = n - n_long
        for a in range(0, n_draw, chunk):
            r = rng.random((min(chunk, n_draw - a), M))
            idx = np.argsort(r, axis=1)[:, :n]
            G = cand[idx]
            stat[a:a + len(G)] += G[:, :n_long].sum(axis=1) - G[:, n_long:n].sum(axis=1)
    nul = stat / n_tot - cost
    p = float((1 + np.sum(nul >= obs - 1e-15)) / (n_draw + 1))
    return p, float(nul.mean()), float(np.quantile(nul, 0.95))


def halves(t: Trades, cost: float = COST) -> dict:
    lo, hi = pd.Timestamp(t.window[0]), pd.Timestamp(t.window[1])
    mid = lo + (hi - lo) / 2
    when = pd.to_datetime(t.entry_date)
    net = t.net(cost)
    first = when <= mid
    out = {"midpoint": str(mid.date())}
    for name, mk in (("first", first), ("second", ~first)):
        out[name + "_n"] = int(mk.sum())
        out[name + "_mean"] = float(net[mk].mean()) if mk.any() else float("nan")
    return out


def evaluate_idea(t: Trades) -> dict:
    """All pre-registered numbers for one idea at cost 0.10% and at cost 0, plus the verdict."""
    net, gross_dir = t.net(COST), t.net(0.0)
    n = len(net)
    res = {"idea": t.idea, "name": t.name, "n_trades": n, "skipped": t.skipped, "window": [str(t.window[0]), str(t.window[1])],
           "win_rate": float((net > 0).mean()) if n else float("nan"),
           "mean_net": float(net.mean()) if n else float("nan"), "mean_gross": float(gross_dir.mean()) if n else float("nan"),
           "boot_p": bootstrap_p(net), "boot_p_zero_cost": bootstrap_p(gross_dir)}
    res["null_p"], res["null_mean"], res["null_q95"] = null_p(t, COST)
    res["null_p_zero_cost"] = null_p(t, 0.0)[0]
    res.update(halves(t, COST))
    res["halves_zero_cost"] = {k: v for k, v in halves(t, 0.0).items() if k.endswith("_mean")}
    res["notes"] = t.notes
    res["verdict"], res["checks"] = verdict(res)
    return res


def verdict(r: dict) -> tuple:
    a = bool(r["n_trades"] > 0 and r["mean_net"] > 0)
    b = bool(r["boot_p"] < ALPHA)
    c = bool(r["null_p"] < ALPHA)
    d_ = bool(r["first_n"] > 0 and r["second_n"] > 0 and r["first_mean"] > 0 and r["second_mean"] > 0)
    e = bool(r["n_trades"] >= MIN_TRADES)
    checks = {"a_mean_net_positive": a, "b_boot_p": b, "c_null_p": c, "d_both_halves_positive": d_, "e_min_60_trades": e}
    if a and b and c and d_ and e:
        return "SURVIVES", checks
    if a and b:
        return "INCONCLUSIVE", checks
    return "REJECT", checks


# ----------------------------------------------------------------------------------------------- lookahead / entry-delay controls (NOT trials)
def delay_check_idea5(d: pd.DataFrame, v: pd.DataFrame) -> dict:
    """Decide at the VIX-spike close, but enter at the NEXT row's open (exit unchanged: close 3 rows after the signal)."""
    t = idea5_vix_panic(d, v)
    C, O = d["close"].values, d["open"].values
    pos = {x: i for i, x in enumerate(_dates(d))}
    i = np.array([pos[x] for x in t.entry_date])
    g = C[i + 3] / O[i + 1] - 1
    return {"n": int(len(i)), "base_mean_gross": float(t.gross.mean()) if len(i) else None, "delayed_mean_gross": float(g.mean()) if len(i) else None}


def delay_check_intraday(m: pd.DataFrame, which: int) -> dict:
    """Same signal, entry one 5-minute bar later (exit unchanged). `which` is 3, 6 or 7. Compared on the SAME trade set."""
    if which == 3:
        b = bars_by_day(m, ("0915", "0920", "1525"))
        d = load_daily()
        d = d[d["date"] >= b.index.min()]
        prevc = d["close"].shift(1).values
        gap = d["open"].values / prevc - 1
        g = pd.Series(gap, index=d["date"]).dropna()
        sig = g[np.abs(g) > 0.007 + EPS]
        bb = b.reindex(sig.index).dropna(subset=["o_0915", "o_0920", "c_1525"])
        s = -np.sign(sig.reindex(bb.index).values)
        base = s * (bb["c_1525"].values / bb["o_0915"].values - 1)
        late = s * (bb["c_1525"].values / bb["o_0920"].values - 1)
    elif which == 6:
        b = bars_by_day(m, ("1415", "1515", "1520", "1525")).dropna(subset=["o_1415", "o_1515", "o_1520", "c_1525"])
        s = np.sign(b["o_1515"].values / b["o_1415"].values - 1)
        base = s * (b["c_1525"].values / b["o_1515"].values - 1)
        late = s * (b["c_1525"].values / b["o_1520"].values - 1)
    else:
        b = bars_by_day(m, ("0915", "0940", "0945", "0950", "1515")).dropna(subset=["o_0915", "c_0940", "o_0945", "o_0950", "o_1515"])
        s = np.sign(b["c_0940"].values / b["o_0915"].values - 1)
        base = s * (b["o_1515"].values / b["o_0945"].values - 1)
        late = s * (b["o_1515"].values / b["o_0950"].values - 1)
    return {"n": int(len(base)), "base_mean_gross": float(base.mean()), "delayed_mean_gross": float(late.mean())}


# ----------------------------------------------------------------------------------------------- run everything
def run_all() -> list:
    d, v, m = load_daily(), load_vix(), load_5min()
    trades = [idea1_sip(d), idea2_overnight(d), idea3_gap_fade(d), idea4_forced_sellers(d), idea5_vix_panic(d, v),
              idea6_closing(m), idea7_morning(m), idea8_preholiday(d), idea9_weekend(d), idea10_expiry(d)]
    return trades


def code_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
