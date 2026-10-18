"""Run the pre-registered delta-neutral study (variants A, B, C x slippage 0.10/0.20/0.30) and apply the fixed PASS RULE.
  python3 research/deltaneutral/evaluate.py            # needs the real option files from download_expired_options.py (never run on partial data)
Reads DEV data only (research/data/). Never touches the hidden holdout. Writes research/deltaneutral/results/*."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scalp" / "options"))
sys.path.insert(0, str(HERE.parent))
import backtest as bt  # noqa: E402
import swing as sw  # noqa: E402
from costs_opt import OptionCostModel  # noqa: E402
from option_book import OptionBook  # noqa: E402

DATA = HERE.parent / "data"
START, CUTOFF = date(2024, 10, 3), date(2026, 4, 16)
SLIPS = (0.10, 0.20, 0.30)
VARIANTS = ("A", "B", "C")
MARGIN_BASE = 120_000.0  # ASSUMPTION: the teacher's quoted Rs1.0-1.2 lakh per lot; real margin unverified
BLOCK, RESAMPLES, SEED = 5, 5000, 20261018
DTE_BUCKETS = [("0", lambda d: d == 0), ("1", lambda d: d == 1), ("2", lambda d: d == 2), ("3-4", lambda d: d in (3, 4)), ("5+", lambda d: d >= 5)]


def load():
    idx5 = pd.read_csv(DATA / "nifty_5minute_dev.csv", parse_dates=["date"])
    cal = sorted(date.fromisoformat(x) for x in pd.read_csv(DATA / "nifty_expiries.csv")["expiry"])
    book = OptionBook(DATA / "expired_options" / "NIFTY")
    return idx5, cal, book


def day_inputs(idx5, cal, book):
    """Per eligible trading day: bars, swing zone (or why not), next expiry. Independent of variant and slippage."""
    d15 = sw.resample_15m(idx5)
    out = []
    days = idx5["date"].dt.date
    for day in sorted(set(days)):
        if not (START <= day <= CUTOFF):
            continue
        bars = idx5[days == day].reset_index(drop=True)
        exp = next((e for e in cal if e >= day), None)
        rec = dict(day=day, bars=bars, expiry=exp, zone=None, why=None)
        e940 = bars[bars["date"] == datetime.combine(day, bt.Params().entry_decision)]
        if e940.empty:
            rec["why"] = "no_entry_bar"
        else:
            prev = sw.previous_sessions(d15, day)
            if prev["date"].dt.date.nunique() < sw.N_SESSIONS:
                rec["why"] = "no_history"
            else:
                z = sw.swing_range(prev, float(e940["close"].iloc[0]))
                if z is None:
                    rec["why"] = "no_swing_range"
                else:
                    rec["zone"] = z
        out.append(rec)
    return out


def run_variant(variant, slip, inputs, book, cache):
    cm = OptionCostModel(slippage_rs=slip)
    rows = []
    for r in inputs:
        base = dict(variant=variant, day=r["day"], expiry=r["expiry"])
        if r["zone"] is None:
            rows.append(dict(base, status="no_signal", reason=r["why"]))
            continue
        if r["expiry"] is None or r["expiry"] > CUTOFF or (r["expiry"], "CE") not in book.strikes or (r["expiry"], "PE") not in book.strikes:
            rows.append(dict(base, status="skipped", reason="no_option_files"))
            continue
        res = bt.run_day(variant, r["bars"], r["zone"][0], r["zone"][1], book, r["expiry"], cm, entry_cache=cache)
        res["dte"] = (r["expiry"] - r["day"]).days
        rows.append(res)
    return rows


# ---------------- statistics ----------------
def block_bootstrap_mean_ci(x, block=BLOCK, n_resamples=RESAMPLES, seed=SEED, alpha=0.05):
    x = np.asarray(x, float)
    n = len(x)
    if n < block + 1:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    nb = -(-n // block)
    starts = rng.integers(0, n - block + 1, size=(n_resamples, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_resamples, -1)[:, :n]
    means = x[idx].mean(axis=1)
    return (float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2)))


def max_drawdown(daily):
    c = np.cumsum(np.asarray(daily, float))
    peak = np.maximum.accumulate(np.r_[0.0, c])[1:]
    return float((c - peak).min()) if len(c) else 0.0  # <= 0


def longest_losing_streak(daily):
    best = cur = 0
    for v in daily:
        cur = cur + 1 if v < 0 else 0
        best = max(best, cur)
    return best


def summarize(rows, capital):
    traded = [r for r in rows if r["status"] == "traded"]
    net = np.array([r["net"] for r in traded], float)
    sk = {}
    for r in rows:
        if r["status"] in ("skipped", "no_signal"):
            sk[r["reason"]] = sk.get(r["reason"], 0) + 1
    n = len(net)
    s = dict(days_in_window=len(rows), traded=n, no_signal={k: v for k, v in sk.items() if k in ("no_swing_range", "no_history")},
             skipped={k: v for k, v in sk.items() if k not in ("no_swing_range", "no_history")})
    if n == 0:
        return s
    ends = {}
    for r in traded:
        ends[r["end_reason"]] = ends.get(r["end_reason"], 0) + 1
    ci = block_bootstrap_mean_ci(net)
    dd = max_drawdown(net)
    months = {}
    for r in traded:
        months.setdefault((r["day"].year, r["day"].month), []).append(r["net"])
    mret = [sum(v) / capital for v in months.values()]
    years = (traded[-1]["day"] - traded[0]["day"]).days / 365.25
    s.update(win_rate=float((net > 0).mean()), mean=float(net.mean()), median=float(np.median(net)), total=float(net.sum()), worst=float(net.min()),
             best=float(net.max()), max_dd=dd, max_dd_pct=dd / capital * 100, losing_streak=longest_losing_streak(net),
             avg_adjust=float(np.mean([r["n_adjust"] for r in traded])), avg_orders=float(np.mean([r["orders"] for r in traded])),
             avg_noop=float(np.mean([r["n_noop"] for r in traded])),
             skipped_adjust=int(sum(r["skipped_adjust"] for r in traded)), skipped_exit=int(sum(r["skipped_exit"] for r in traded)),
             forced_close_days=int(sum(1 for r in traded if r["forced"])),
             breakout_days=int(sum(1 for r in traded if r["breakout"] or r["end_reason"] == "range_exit")),
             end_reasons={k: v / n for k, v in sorted(ends.items())}, mean_ci95=ci, gross_mean=float(np.mean([r["gross"] for r in traded])),
             cost_mean=float(np.mean([r["cost"] for r in traded])), capital=capital,
             monthly_pct=float(np.mean(mret) * 100), monthly_pct_min=float(np.min(mret) * 100), monthly_pct_max=float(np.max(mret) * 100),
             annual_pct_simple=float(np.mean(mret) * 12 * 100), total_return_pct=float(net.sum() / capital * 100), years=years,
             months=len(months), top5_loss_share=float(np.sort(net)[:5].sum() / net[net < 0].sum()) if (net < 0).any() else 0.0,
             first_half_mean=float(net[: n // 2].mean()), second_half_mean=float(net[n // 2:].mean()),
             mean_entry_call_delta=float(np.mean([r["entry"]["call_delta"] for r in traded])),
             mean_entry_put_delta=float(np.mean([r["entry"]["put_delta"] for r in traded])))
    return s


def dte_table(rows):
    out = {}
    traded = [r for r in rows if r["status"] == "traded"]
    for name, f in DTE_BUCKETS:
        v = np.array([r["net"] for r in traded if f(r["dte"])], float)
        out[name] = dict(days=len(v), mean=float(v.mean()) if len(v) else None, total=float(v.sum()) if len(v) else 0.0,
                         win_rate=float((v > 0).mean()) if len(v) else None, worst=float(v.min()) if len(v) else None)
    return out


def pass_rule(res):
    """Fixed pre-registered rule, evaluated at slippage 0.20 (a, b, d) and 0.30 (c)."""
    s20, s30 = res[0.20], res[0.30]
    if not s20.get("traded"):
        return dict(useful=False, a=False, b=False, c=False, d=False)
    a = s20["mean"] > 0 and s20["mean_ci95"][0] > 0
    b = s20["total"] >= 3 * abs(min(s20["worst"], 0.0)) if s20["worst"] < 0 else s20["total"] > 0
    c = s30["mean"] > 0
    d = abs(min(s20["worst"], 0.0)) < 0.05 * s20["capital"]
    return dict(a=bool(a), b=bool(b), c=bool(c), d=bool(d), useful=bool(a and b and c and d))


def main():
    idx5, cal, book = load()
    need = {e for e in cal if START <= e <= CUTOFF}
    have = {k[0] for k in book.t}
    missing = sorted(need - have)
    print(f"option files for {len(have)} expiries; dev expiries needed {len(need)}; missing {len(missing)}: {missing[:6]}")
    inputs = day_inputs(idx5, cal, book)
    print(f"{len(inputs)} trading days in window; swing rule passes on {sum(1 for r in inputs if r['zone'])}")
    cache: dict = {}
    allres, daily = {}, {}
    # C's capital base needs the widest hedged structure seen, so run C first at every slippage
    for v in ("C", "A", "B"):
        allres[v], daily[v] = {}, {}
        for slip in SLIPS:
            daily[v][slip] = run_variant(v, slip, inputs, book, cache)
    widest = max((r["max_width_pts"] for s in SLIPS for r in daily["C"][s] if r["status"] == "traded"), default=0.0)
    cap_c = MARGIN_BASE + bt.Params().qty * 2 * widest  # max possible intraday loss (sum of widths) + the same Rs1.2 lakh
    caps = dict(A=MARGIN_BASE, B=MARGIN_BASE, C=cap_c)
    for v in VARIANTS:
        for slip in SLIPS:
            allres[v][slip] = summarize(daily[v][slip], caps[v])
    out = dict(run_date=str(date.today()), window=[str(START), str(CUTOFF)], slips=list(SLIPS), capital=caps, widest_wing_structure_pts=widest,
               missing_expiries=[str(e) for e in missing], summary={v: {str(s): allres[v][s] for s in SLIPS} for v in VARIANTS},
               dte={v: {str(s): dte_table(daily[v][s]) for s in SLIPS} for v in VARIANTS},
               pass_rule={v: pass_rule(allres[v]) for v in VARIANTS},
               code_sha256=hashlib.sha256((HERE / "backtest.py").read_bytes()).hexdigest()[:16])
    # C on a Rs1.2 lakh denominator, for comparison only (not the pre-registered base)
    out["C_on_margin_only"] = {str(s): summarize(daily["C"][s], MARGIN_BASE).get("monthly_pct") for s in SLIPS}
    res_dir = HERE / "results"
    res_dir.mkdir(exist_ok=True)
    (res_dir / "dn_results.json").write_text(json.dumps(out, indent=1, default=str))
    for v in VARIANTS:
        for s in SLIPS:
            recs = [{k: (str(x) if k in ("day", "expiry") else x) for k, x in r.items() if k not in ("events", "entry", "bars")} for r in daily[v][s]]
            pd.DataFrame(recs).to_csv(res_dir / f"daily_{v}_{s:.2f}.csv", index=False)
    # trial ledger: 3 variants, one run each
    with open(HERE / "ledger_deltaneutral.jsonl", "a") as f:
        for v in VARIANTS:
            f.write(json.dumps(dict(date=str(date.today()), study="deltaneutral", variant=v, code_sha256=out["code_sha256"], slippages=list(SLIPS),
                                    window=out["window"], useful=out["pass_rule"][v]["useful"])) + "\n")
    # full event logs of every traded day at slippage 0.20 (for crosscheck.py, which re-prices them from the raw candle files)
    for v in VARIANTS:
        ev_log = [dict(day=str(r["day"]), expiry=str(r["expiry"]), net=r["net"], gross=r["gross"], cost=r["cost"], orders=r["orders"],
                       events=[{k: (str(x) if k in ("decision_ts", "fill_ts") else x) for k, x in e.items()} for e in r["events"]])
                  for r in daily[v][0.20] if r["status"] == "traded"]
        (res_dir / f"events_{v}_0.20.json").write_text(json.dumps(ev_log, default=str))
    # keep the event logs of the 6 worst days of each variant at slippage 0.20 for the review
    worst = {}
    for v in VARIANTS:
        tr = sorted([r for r in daily[v][0.20] if r["status"] == "traded"], key=lambda r: r["net"])[:6]
        worst[v] = [dict(day=str(r["day"]), expiry=str(r["expiry"]), dte=r["dte"], net=r["net"], end_reason=r["end_reason"], n_adjust=r["n_adjust"],
                         entry=r["entry"], events=[{k: str(x) for k, x in e.items()} for e in r["events"]]) for r in tr]
    (res_dir / "worst_days.json").write_text(json.dumps(worst, indent=1, default=str))
    print(json.dumps(out["pass_rule"]))
    return out


if __name__ == "__main__":
    main()
