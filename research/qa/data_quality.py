"""Data-quality checks for the market data this repo downloads (checklist: .claude/skills/market-data-engineering).

Nothing is ever deleted or repaired here: every check only REPORTS. Each finding has a category, a count and a few examples.

  python research/qa/data_quality.py                   # index bars, daily bars, VIX, expiry calendar
  python research/qa/data_quality.py --options         # also the saved expired-option files
Reads dev data only (research/data). It never opens the hidden holdout.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
DATA = HERE.parent / "data"
OHLC = ["open", "high", "low", "close"]
SESSION_OPEN, SESSION_CLOSE = time(9, 15), time(15, 30)
SIGMA = 5.0  # outlier threshold in standard deviations
DAILY_TOL = 0.001  # 0.10%: allowed gap between aggregated 5-minute bars and the daily bar


@dataclass
class Finding:
    dataset: str
    category: str
    count: int
    detail: str = ""
    examples: list = field(default_factory=list)

    def line(self) -> str:
        ex = f"  e.g. {', '.join(map(str, self.examples[:4]))}" if self.examples else ""
        return f"  [{self.category}] {self.count}  {self.detail}{ex}"


def _add(out: list, dataset: str, category: str, mask_or_n, detail: str = "", examples=None):
    n = int(mask_or_n.sum()) if hasattr(mask_or_n, "sum") else int(mask_or_n)
    if n:
        out.append(Finding(dataset, category, n, detail, list(examples) if examples is not None else []))


def _dates(s: pd.Series) -> list:
    return [pd.Timestamp(x).strftime("%Y-%m-%d") for x in s]


def _integrity(df: pd.DataFrame, name: str, out: list):
    """Checks shared by every OHLC table: columns, NaN, duplicates, order, non-positive prices, impossible bars."""
    missing = [c for c in ["date", *OHLC] if c not in df.columns]
    if missing:
        _add(out, name, "schema", len(missing), f"missing columns {missing}")
        return False
    _add(out, name, "nan", df[["date", *OHLC]].isna().any(axis=1), "rows with a NaN in date/open/high/low/close",
         _dates(df.loc[df[["date", *OHLC]].isna().any(axis=1), "date"].dropna()))
    dup = df["date"].duplicated(keep=False)
    _add(out, name, "duplicate_timestamp", df["date"].duplicated(), "rows repeating an earlier timestamp", _dates(df.loc[dup, "date"]))
    _add(out, name, "unsorted", (df["date"].diff() < pd.Timedelta(0)), "rows earlier than the row before them")
    px = df[OHLC]
    _add(out, name, "nonpositive_price", (px <= 0).any(axis=1), "rows with a price <= 0", _dates(df.loc[(px <= 0).any(axis=1), "date"]))
    bad_hl = df["high"] < df["low"]
    _add(out, name, "high_below_low", bad_hl, "rows with high < low", _dates(df.loc[bad_hl, "date"]))
    out_rng = ((df["open"] > df["high"]) | (df["open"] < df["low"]) | (df["close"] > df["high"]) | (df["close"] < df["low"])) & ~bad_hl
    _add(out, name, "ohlc_outside_range", out_rng, "rows where open or close lies outside [low, high]", _dates(df.loc[out_rng, "date"]))
    return True


def _outliers(ret: pd.Series, dates: pd.Series):
    z = (ret - ret.mean()) / ret.std()
    hit = z.abs() > SIGMA
    return hit, z


def check_intraday(df: pd.DataFrame, daily: pd.DataFrame | None = None, bar_minutes: int = 5, name: str = "5min bars") -> list[Finding]:
    out: list[Finding] = []
    df = df.copy()
    if not _integrity(df, name, out):
        return out
    d = df["date"]
    if getattr(d.dt, "tz", None) is not None:
        _add(out, name, "timezone", len(d), "timestamps are tz-aware; the repo convention is naive IST")
        d = d.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        df["date"] = d
    tod = d.dt.time
    last_start = (pd.Timestamp("2000-01-01 15:30") - pd.Timedelta(minutes=bar_minutes)).time()
    off = (tod < SESSION_OPEN) | (tod > last_start)
    _add(out, name, "outside_session_hours", off, f"bars starting outside 09:15-{last_start:%H:%M}", _dates(d[off]))
    mins = (d.dt.hour * 60 + d.dt.minute) - (9 * 60 + 15)
    _add(out, name, "misaligned_bar", (mins % bar_minutes != 0) & ~off, f"bar start not on the {bar_minutes}-minute grid from 09:15")
    wk = d.dt.dayofweek >= 5
    wk_days = sorted(set(_dates(d[wk])))
    _add(out, name, "weekend_days", len(wk_days), f"Saturday/Sunday dates with bars ({int(wk.sum())} bars; Budget days and special sessions are real, confirm each)", wk_days)

    day = d.dt.normalize()
    per_day = df.groupby(day).size()
    full = 375 // bar_minutes  # 09:15-15:30 is 375 minutes
    short = per_day[per_day < full]
    long_ = per_day[per_day > full]
    _add(out, name, "short_day", len(short), f"trading days with fewer than {full} bars (half-days/special sessions, or missing bars)",
         [f"{k:%Y-%m-%d}:{v}" for k, v in short.items()])
    _add(out, name, "long_day", len(long_), f"days with more than {full} bars", [f"{k:%Y-%m-%d}:{v}" for k, v in long_.items()])
    # gaps INSIDE a day = bars genuinely missing (a truncated session just ends early)
    clean = df[~df["date"].duplicated()].sort_values("date")
    gap = clean["date"].diff()
    same = clean["date"].dt.normalize() == clean["date"].dt.normalize().shift()
    inner = same & (gap > pd.Timedelta(minutes=bar_minutes))
    _add(out, name, "intraday_gap", inner, "places where bars are missing inside a session",
         [f"{t:%Y-%m-%d %H:%M}" for t in clean.loc[inner, "date"]])
    _add(out, name, "missing_bars_in_gaps", int(((gap[inner] / pd.Timedelta(minutes=bar_minutes)) - 1).sum()), "total bars missing inside sessions")
    late_start = clean.groupby(clean["date"].dt.normalize())["date"].min().dt.time > SESSION_OPEN
    _add(out, name, "late_first_bar", late_start, "days whose first bar is after 09:15")

    # outliers: within-day close-to-close log return > 5 sigma. Verified against the daily bar; never dropped.
    c = clean.reset_index(drop=True)
    r = np.log(c["close"]).diff()
    r[(c["date"].dt.normalize() != c["date"].dt.normalize().shift()).values] = np.nan  # skip the overnight gap
    ok = r.notna()
    hit, z = _outliers(r[ok], c.loc[ok, "date"])
    nxt = r.shift(-1)
    reverts = (np.sign(nxt) != np.sign(r)) & (nxt.abs() >= 0.8 * r.abs())  # next bar undoes >= 80% of the move: a bad-tick signature
    if hit.any():
        _add(out, name, "outlier_reverting", int((hit & reverts[ok]).sum()), "outlier bars whose next bar undoes >= 80% of the move (bad-tick signature; also happens in real whipsaws)")
        by_day = c.loc[hit[hit].index, "date"].dt.normalize().value_counts()
        _add(out, name, "outlier_clustered_days", int((by_day >= 3).sum()), "days holding 3+ outlier bars (real events cluster; isolated ones are suspect)",
             [f"{k:%Y-%m-%d}:{v}" for k, v in by_day[by_day >= 3].items()])
        idx = hit[hit].index
        dd = None if daily is None else daily.set_index(daily["date"].dt.normalize())
        confirmed, unconfirmed, ex = 0, 0, []
        for i in idx:
            t = c.loc[i, "date"]
            row = None if dd is None else dd.loc[t.normalize()] if t.normalize() in dd.index else None
            inside = row is not None and c.loc[i, "high"] <= row["high"] * (1 + DAILY_TOL) and c.loc[i, "low"] >= row["low"] * (1 - DAILY_TOL)
            confirmed += int(inside)
            unconfirmed += int(not inside)
            ex.append(f"{t:%Y-%m-%d %H:%M} z={z[i]:+.1f}{'' if inside else ' NOT-IN-DAILY-BAR'}")
        _add(out, name, "outlier_5sigma", len(idx), f"bar returns beyond {SIGMA:.0f} sigma ({confirmed} inside the daily bar's high/low, {unconfirmed} not or no daily bar); kept, not dropped", ex)
        _add(out, name, "outlier_unconfirmed", unconfirmed, "outlier bars NOT confirmed by the daily bar: likely bad ticks")

    if daily is not None:
        out += _vs_daily(clean, daily, name)
    return out


def _vs_daily(clean: pd.DataFrame, daily: pd.DataFrame, name: str) -> list[Finding]:
    out: list[Finding] = []
    g = clean.groupby(clean["date"].dt.normalize())
    agg = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last()})
    dd = daily.copy()
    dd.index = dd["date"].dt.normalize()
    common = agg.index.intersection(dd.index)
    lo, hi = agg.index.min(), agg.index.max()
    dd_in = dd[(dd.index >= lo) & (dd.index <= hi)]
    no_intra = dd_in.index.difference(agg.index)
    no_daily = agg.index.difference(dd.index)
    _add(out, name, "missing_day_vs_daily", len(no_intra), "days in the daily file (within the 5-min span) with no 5-min bars", _dates(no_intra))
    _add(out, name, "day_not_in_daily_file", len(no_daily), "days with 5-min bars but no daily bar", _dates(no_daily))
    for col in OHLC:
        rel = ((agg.loc[common, col] - dd.loc[common, col]) / dd.loc[common, col]).abs()
        bad = rel[rel > DAILY_TOL]
        _add(out, name, f"vs_daily_{col}", len(bad), f"days where aggregated 5-min {col} differs from the daily {col} by > {DAILY_TOL:.2%} (max {rel.max():.3%})",
             [f"{k:%Y-%m-%d}:{v:.2%}" for k, v in bad.sort_values(ascending=False).items()])
    return out


def check_daily(df: pd.DataFrame, name: str = "daily bars") -> list[Finding]:
    out: list[Finding] = []
    df = df.copy()
    if not _integrity(df, name, out):
        return out
    d = df["date"]
    _add(out, name, "weekend_days", d.dt.dayofweek >= 5, "daily bars on Saturday/Sunday (Budget days and special sessions are real; confirm each)", _dates(d[d.dt.dayofweek >= 5]))
    ds = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    gap = ds["date"].diff().dt.days
    big = gap > 4
    _add(out, name, "calendar_gap_over_4d", big, "gaps of more than 4 calendar days between daily bars (long holiday clusters are normal; confirm)",
         [f"{ds.loc[i - 1, 'date']:%Y-%m-%d}->{ds.loc[i, 'date']:%Y-%m-%d}" for i in big[big].index])
    yr = ds.groupby(ds["date"].dt.year).size()
    thin = yr[(yr < 240) & (yr.index > ds["date"].min().year) & (yr.index < ds["date"].max().year)]
    _add(out, name, "thin_year", len(thin), "full calendar years with fewer than 240 trading days (NSE normally has about 245-250)", [f"{k}:{v}" for k, v in thin.items()])
    r = np.log(ds["close"]).diff().dropna()
    hit, z = _outliers(r, ds["date"])
    _add(out, name, "outlier_5sigma", hit, f"daily close-to-close returns beyond {SIGMA:.0f} sigma (kept; compare with known events)",
         [f"{ds.loc[i, 'date']:%Y-%m-%d} z={z[i]:+.1f}" for i in hit[hit].index])
    rng = (ds["high"] - ds["low"]) / ds["close"]
    _add(out, name, "zero_range_day", rng == 0, "days with high == low")
    return out


def check_vix(vix: pd.DataFrame, daily: pd.DataFrame | None = None, dev_cut: pd.Timestamp | None = None, name: str = "india vix") -> list[Finding]:
    out: list[Finding] = []
    v = vix.copy()
    for col, what in (("date", "dates"), ("close", "values")):
        if col not in v.columns:
            _add(out, name, "schema", 1, f"missing column {col}")
            return out
    _add(out, name, "nan", v[["date", "close"]].isna().any(axis=1), "rows with NaN")
    _add(out, name, "duplicate_timestamp", v["date"].duplicated(), "repeated dates", _dates(v.loc[v["date"].duplicated(), "date"]))
    _add(out, name, "unsorted", v["date"].diff() < pd.Timedelta(0), "rows earlier than the row before them")
    _add(out, name, "nonpositive_price", v["close"] <= 0, "VIX <= 0")
    _add(out, name, "implausible_level", (v["close"] < 5) | (v["close"] > 100), "VIX outside [5, 100] (record low is about 8.5, record high about 86)",
         [f"{a:%Y-%m-%d}:{b}" for a, b in zip(v.loc[(v['close'] < 5) | (v['close'] > 100), 'date'], v.loc[(v['close'] < 5) | (v['close'] > 100), 'close'])])
    _add(out, name, "weekend_days", v["date"].dt.dayofweek >= 5, "VIX rows on a weekend", _dates(v.loc[v["date"].dt.dayofweek >= 5, "date"]))
    s = v.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    r = np.log(s["close"].where(s["close"] > 0)).diff().dropna()
    hit, z = _outliers(r, s["date"])
    _add(out, name, "outlier_5sigma", hit, f"day-over-day log changes beyond {SIGMA:.0f} sigma (kept)", [f"{s.loc[i, 'date']:%Y-%m-%d} z={z[i]:+.1f}" for i in hit[hit].index])
    run = (s["close"] != s["close"].shift()).cumsum()
    stale = s.groupby(run).size()
    _add(out, name, "stale_value", int((stale >= 5).sum()), "runs of 5+ identical consecutive VIX closes", [f"len {n}" for n in stale[stale >= 5]])
    if daily is not None:
        dd = set(daily["date"].dt.normalize())
        vd = set(s["date"].dt.normalize())
        lo, hi = min(dd), max(dd)
        only_v = sorted(x for x in vd if lo <= x <= hi and x not in dd)
        only_d = sorted(x for x in dd if min(vd) <= x <= max(vd) and x not in vd)
        _add(out, name, "date_in_vix_not_in_daily", len(only_v), "VIX dates inside the daily span with no NIFTY daily bar", _dates(only_v))
        _add(out, name, "date_in_daily_not_in_vix", len(only_d), "NIFTY trading days inside the VIX span with no VIX row", _dates(only_d))
    if dev_cut is not None:
        beyond = v["date"] > dev_cut
        _add(out, name, "beyond_dev_cutoff", beyond, f"rows dated after the dev cut-off {dev_cut:%Y-%m-%d}: this file is not split like the index bars (holdout-window values sit in the dev folder)",
             [f"{v.loc[beyond, 'date'].min():%Y-%m-%d} to {v.loc[beyond, 'date'].max():%Y-%m-%d}"] if beyond.any() else [])
    return out


def check_expiries(ex: pd.DataFrame, daily: pd.DataFrame | None = None, dev_cut: pd.Timestamp | None = None, today: pd.Timestamp | None = None,
                   name: str = "expiry calendar") -> list[Finding]:
    out: list[Finding] = []
    if "expiry" not in ex.columns:
        _add(out, name, "schema", 1, "missing column expiry")
        return out
    e = pd.to_datetime(ex["expiry"], errors="coerce")
    _add(out, name, "unparseable", e.isna(), "expiry values that are not dates")
    e = e.dropna()
    _add(out, name, "duplicate_timestamp", e.duplicated(), "repeated expiries", _dates(e[e.duplicated()]))
    _add(out, name, "unsorted", e.diff() < pd.Timedelta(0), "expiries out of order")
    s = e.drop_duplicates().sort_values().reset_index(drop=True)
    wd = s.dt.dayofweek
    _add(out, name, "weekend_expiry", wd >= 5, "expiry on Saturday/Sunday", _dates(s[wd >= 5]))
    gap = s.diff().dt.days
    odd = gap[(gap != 7) & gap.notna()]
    _add(out, name, "gap_not_7_days", len(odd), "weekly gaps that are not exactly 7 days (a holiday moves an expiry earlier; a weekday change shows here too)",
         [f"{s[i - 1]:%Y-%m-%d}->{s[i]:%Y-%m-%d} ({int(g)}d)" for i, g in odd.items()])
    chg = wd != wd.shift()
    chg.iloc[0] = False
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    _add(out, name, "weekday_changes", chg, "points where the expiry weekday changes (rule change; do not assume one weekday for the whole history)",
         [f"{s[i]:%Y-%m-%d}: {names[wd[i - 1]]}->{names[wd[i]]}" for i in chg[chg].index])
    if daily is not None:
        days = set(daily["date"].dt.normalize())
        lo, hi = min(days), max(days)
        inside = s[(s >= lo) & (s <= hi)]
        nt = inside[~inside.isin(days)]
        _add(out, name, "expiry_not_a_trading_day", len(nt), "expiries inside the daily-bar span that were not trading days", _dates(nt))
        _add(out, name, "expiry_beyond_daily_data", int((s > hi).sum()), f"expiries after the last daily bar ({hi:%Y-%m-%d}); cannot be checked against trading days")
    if today is not None:
        _add(out, name, "future_expiry", s > today, "expiries dated after today in an EXPIRED-instruments list")
    if dev_cut is not None:
        beyond = s > dev_cut
        _add(out, name, "beyond_dev_cutoff", beyond, f"expiries after the dev cut-off {dev_cut:%Y-%m-%d} (holdout window); the calendar file is not split like the index bars")
    return out


# ---------------------------------------------------------------- option files

OPT_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d+)(CE|PE)\.csv$")


def parse_opt_name(p: Path):
    m = OPT_NAME.match(p.name)
    return (pd.Timestamp(m.group(1)), int(m.group(2)), m.group(3)) if m else None


def check_option_file(df: pd.DataFrame, fname: str, bar_minutes: int = 5) -> list[Finding]:
    """One expired-option candle file. Option bars legitimately have gaps (no trades); the gaps are COUNTED, not treated as errors."""
    out: list[Finding] = []
    df = df.copy()
    if not _integrity(df, fname, out):
        return out
    d = df["date"]
    t = d.dt.time
    off = (t < SESSION_OPEN) | (t > time(15, 25))
    _add(out, fname, "outside_session_hours", off, "bars outside 09:15-15:25")
    for col in ("volume", "oi"):
        if col in df.columns:
            _add(out, fname, f"negative_{col}", df[col] < 0, f"{col} < 0")
            _add(out, fname, f"nan_{col}", df[col].isna(), f"{col} is NaN")
    if "volume" in df.columns:
        flat = (df["high"] == df["low"]) & (df["volume"] == 0)
        _add(out, fname, "zero_volume_flat_bar", flat, "bars with no volume and high == low (a carried-forward price, not a trade)")
        _add(out, fname, "zero_volume_bar", df["volume"] == 0, "bars with volume 0")
    return out


def option_file_stats(df: pd.DataFrame, bar_minutes: int = 5) -> dict:
    """Candle coverage of one option file on the days it has data: expected bars vs bars present."""
    d = df["date"]
    per_day = df.groupby(d.dt.normalize()).size()
    return {"rows": len(df), "days": len(per_day), "expected": 75 * len(per_day), "present": int(per_day.sum())}


def check_options(folder: Path, daily5: pd.DataFrame, daily: pd.DataFrame, spot_step: int = 50, strikes_n: int | None = None) -> tuple[list[Finding], dict]:
    """Checks across a folder of option files: per-file integrity, candle coverage, strike coverage vs where spot actually traded, volume/OI anomalies."""
    out: list[Finding] = []
    stats = {"files": 0, "expiries": 0}
    files = sorted(p for p in folder.glob("*.csv") if parse_opt_name(p))
    bad_names = [p.name for p in folder.glob("*.csv") if not parse_opt_name(p)]
    _add(out, str(folder), "unparseable_filename", len(bad_names), "files not named <expiry>_<strike><CE|PE>.csv", bad_names)
    if not files:
        return out, stats
    spot = daily5.copy()
    spot["day"] = spot["date"].dt.normalize()
    by_exp: dict = {}
    cov_expected = cov_present = zero_vol = rows = 0
    oi_jump: list = []
    vol_spike: list = []
    pre_cut_rows = after_expiry_rows = 0
    for p in files:
        exp, strike, typ = parse_opt_name(p)
        df = pd.read_csv(p, parse_dates=["date"])
        stats["files"] += 1
        rows += len(df)
        if len(df) == 0:
            _add(out, p.name, "empty_file", 1, "no rows")
            continue
        out += check_option_file(df, p.name)
        by_exp.setdefault(exp, set()).add((strike, typ))
        s = option_file_stats(df)
        cov_expected += s["expected"]
        cov_present += s["present"]
        zero_vol += int((df["volume"] == 0).sum()) if "volume" in df.columns else 0
        after_expiry_rows += int((df["date"].dt.normalize() > exp).sum())
        if "oi" in df.columns and len(df) > 5:
            oi = df["oi"].astype(float)
            ch = oi.diff().abs()
            base = max(oi.median(), 1.0)
            big = ch > 5 * base  # open interest jumps by > 5x its median inside one 5-minute bar
            if big.any():
                oi_jump.append(f"{p.name}:{int(big.sum())}")
        if "volume" in df.columns and len(df) > 20:
            v = df["volume"].astype(float)
            med = v[v > 0].median() if (v > 0).any() else 0
            if med > 0 and (v > 50 * med).any():
                vol_spike.append(f"{p.name}:{int((v > 50 * med).sum())}")
    stats["expiries"] = len(by_exp)
    stats["rows"] = rows
    _add(out, "option files", "candle_coverage_gap", cov_expected - cov_present,
         f"bars missing on days an option file has data: {cov_present} of {cov_expected} expected 75-bar days present ({cov_present / max(cov_expected, 1):.1%})")
    _add(out, "option files", "zero_volume_share", zero_vol, f"zero-volume bars: {zero_vol / max(rows, 1):.1%} of {rows} rows")
    _add(out, "option files", "rows_after_expiry_date", after_expiry_rows, "rows dated after the contract's expiry")
    _add(out, "option files", "oi_jump", len(oi_jump), "files with an open-interest jump above 5x its median inside one bar", oi_jump)
    _add(out, "option files", "volume_spike", len(vol_spike), "files with a bar whose volume is above 50x the file's median non-zero volume", vol_spike)

    # strike coverage: for each expiry, which strikes were saved vs where spot actually traded in the contract's life
    lo_miss = []
    skipped_bar_days = total_bar_days = 0
    window = 9  # days a weekly contract trades before expiry (download_expired_options.py UNDERLYINGS['NIFTY']['days'])
    for exp, have in sorted(by_exp.items()):
        strikes = sorted({k for k, _ in have})
        for typ in ("CE", "PE"):
            n = sum(1 for k, t in have if t == typ)
            if n != len(strikes):
                lo_miss.append(f"{exp:%Y-%m-%d}:{typ} has {n} of {len(strikes)} strikes")
        sp = spot[(spot["day"] >= exp - pd.Timedelta(days=window)) & (spot["day"] <= exp)]
        if sp.empty:
            continue
        lo_s, hi_s = strikes[0], strikes[-1]
        # a spot bar's nearest strike (ATM) outside the saved range means signals on that bar could not be priced
        atm = (sp["close"] / spot_step).round() * spot_step
        outside = (atm < lo_s) | (atm > hi_s)
        total_bar_days += len(sp)
        skipped_bar_days += int(outside.sum())
    _add(out, "option files", "strike_asymmetry", len(lo_miss), "expiries where CE and PE do not have the same strikes saved", lo_miss)
    _add(out, "option files", "spot_outside_saved_strikes", skipped_bar_days,
         f"5-min bars (in each contract's life window) whose ATM strike lies outside the saved strike range: {skipped_bar_days / max(total_bar_days, 1):.1%} of {total_bar_days} bars")
    stats["strike_ranges"] = {f"{k:%Y-%m-%d}": (min(s for s, _ in v), max(s for s, _ in v)) for k, v in by_exp.items()}
    return out, stats


# ---------------------------------------------------------------- driver

def report(findings: list[Finding]) -> str:
    lines = []
    cur = None
    for f in findings:
        if f.dataset != cur:
            cur = f.dataset
            lines.append(cur)
        lines.append(f.line())
    return "\n".join(lines) if lines else "(no findings)"


def run_all(include_options: bool = False) -> list[Finding]:
    out: list[Finding] = []
    p5, pd_, pv, pe = DATA / "nifty_5minute_dev.csv", DATA / "nifty_day_dev.csv", DATA / "india_vix_day.csv", DATA / "nifty_expiries.csv"
    d5 = pd.read_csv(p5, parse_dates=["date"]) if p5.exists() else None
    dd = pd.read_csv(pd_, parse_dates=["date"]) if pd_.exists() else None
    vx = pd.read_csv(pv, parse_dates=["date"]) if pv.exists() else None
    ex = pd.read_csv(pe) if pe.exists() else None
    cut = d5["date"].max().normalize() if d5 is not None else None
    if d5 is not None:
        out += check_intraday(d5, dd)
    if dd is not None:
        out += check_daily(dd)
    if vx is not None:
        out += check_vix(vx, dd, cut)
    if ex is not None:
        out += check_expiries(ex, dd, cut, pd.Timestamp.today().normalize())
    if include_options and d5 is not None:
        f, st = check_options(DATA / "expired_options" / "NIFTY", d5, dd)
        out += f
        print(f"option files: {st.get('files')} files, {st.get('expiries')} expiries, {st.get('rows')} rows")
    return out


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--options", action="store_true")
    a = a.parse_args()
    fs = run_all(a.options)
    print(report(fs))
    print("\nFINDINGS BY CATEGORY (category, count):")
    tot: dict = {}
    for f in fs:
        tot[f.category] = tot.get(f.category, 0) + f.count
    for k, v in sorted(tot.items()):
        print(f"  {k:32s} {v}")
    sys.exit(0)
