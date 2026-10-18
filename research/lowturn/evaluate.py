"""Evaluate B0 / S1 / S2 / S3 on DEV daily NIFTY (2000 .. 6 months before today). Prints JSON, writes results tables.

Run from research/:   python lowturn/evaluate.py [--no-controls]
Reads only research/data/nifty_day_long_dev.csv (the hidden holdout is never read).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import backtest as bt  # noqa: E402
import kite_data as kd  # noqa: E402

OUT = HERE / "results"
LEDGER = HERE / "ledger_lowturn.jsonl"
HEADLINE = 0.0025
NAMES = ["B0", "S1", "S2", "S3"]


def load() -> pd.DataFrame:
    return pd.read_csv(kd.DEV_DIR / "nifty_day_long_dev.csv", parse_dates=["date"])


def signals(df: pd.DataFrame) -> dict[str, pd.Series]:
    return {"B0": bt.signal_buyhold(df), "S1": bt.signal_sma(df), "S2": bt.signal_monthly(df), "S3": bt.signal_voltarget(df)}


def common_start(sig: dict[str, pd.Series]) -> int:
    return max(int(np.flatnonzero(~np.isnan(s.to_numpy()))[0]) for s in sig.values())


def useful(s: dict, b: dict) -> dict:
    """Pre-registered rule for ONE period. s, b = metrics at the headline cost."""
    d = (s["cagr"] - b["cagr"]) * 100
    dd_s, dd_b = abs(s["max_dd"]), abs(b["max_dd"])
    a = d >= -1.5 and dd_s <= 0.7 * dd_b
    c = d >= 1.0 and dd_s <= dd_b
    return {"cagr_diff_pp": d, "dd_ratio": dd_s / dd_b, "clause_A": bool(a), "clause_B": bool(c), "ok": bool(a or c)}


def placebo(df, w_s1: pd.Series, start: int, n=1000, seed=0) -> dict:
    """Random on/off schedules with the same average ON/OFF run lengths as S1 (so same % invested and switch rate)."""
    w = w_s1.to_numpy()[start:]
    on_len = np.diff(np.flatnonzero(np.diff(np.r_[0, w, 0]) != 0))[::2].mean()
    runs = np.diff(np.r_[0, np.flatnonzero(np.diff(w) != 0) + 1, len(w)])
    first_on = w[0] == 1
    on_runs, off_runs = (runs[0::2], runs[1::2]) if first_on else (runs[1::2], runs[0::2])
    p_off, p_on = 1 / on_runs.mean(), 1 / off_runs.mean()
    rng = np.random.default_rng(seed)
    res_calmar, res_dd, res_cagr = [], [], []
    for _ in range(n):
        u = rng.random(len(df))
        x = np.empty(len(df))
        x[:] = np.nan
        state = 1.0
        for t in range(start, len(df)):
            if state == 1.0 and u[t] < p_off:
                state = 0.0
            elif state == 0.0 and u[t] < p_on:
                state = 1.0
            x[t] = state
        m = bt.metrics(bt.run(df, pd.Series(x), HEADLINE, start=start))
        res_calmar.append(m["calmar"]); res_dd.append(m["max_dd"]); res_cagr.append(m["cagr"])
    return {"n": n, "mean_on_run_days": float(on_runs.mean()), "mean_off_run_days": float(off_runs.mean()),
            "placebo_cagr_mean": float(np.mean(res_cagr)), "placebo_maxdd_mean": float(np.mean(res_dd)),
            "placebo_calmar_mean": float(np.mean(res_calmar)), "placebo_calmar_p95": float(np.percentile(res_calmar, 95)),
            "placebo_maxdd_p05": float(np.percentile(res_dd, 5)), "placebo_maxdd_p50": float(np.percentile(res_dd, 50)),
            "placebo_cagr_p95": float(np.percentile(res_cagr, 95)), "placebo_cagr_p05": float(np.percentile(res_cagr, 5))}


def pct(x):
    return f"{100 * x:.1f}%"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-controls", action="store_true")
    a = ap.parse_args()
    df = load()
    sig = signals(df)
    start = common_start(sig)
    out: dict = {"data": {"bars": len(df), "first": str(df.date.iloc[0].date()), "last": str(df.date.iloc[-1].date()),
                          "eval_first_decision": str(df.date.iloc[start].date()), "price_index_excludes_dividends": True,
                          "cash_rate": bt.CASH_RATE}, "results": {}, "halves": {}, "years": {}, "bootstrap": {}, "tax": {}, "pass_rule": {}}
    runs = {c: {n: bt.run(df, sig[n], c, start=start) for n in NAMES} for c in bt.COSTS}
    for c in bt.COSTS:
        out["results"][f"{c:.4f}"] = {n: bt.metrics(runs[c][n]) for n in NAMES}
        h = {}
        for n in NAMES:
            r1, r2 = bt.halves(runs[c][n])
            h[n] = {"first_half": bt.metrics(r1), "second_half": bt.metrics(r2),
                    "first_half_dates": [str(r1.date.iloc[0].date()), str(r1.date.iloc[-1].date())],
                    "second_half_dates": [str(r2.date.iloc[0].date()), str(r2.date.iloc[-1].date())]}
        out["halves"][f"{c:.4f}"] = h
    yrs = pd.DataFrame({n: bt.calendar_years(runs[HEADLINE][n]) for n in NAMES})
    out["years"] = {str(k): {n: float(v) for n, v in row.items()} for k, row in yrs.iterrows()}
    # pre-registered pass rule at headline cost
    hl, hh = out["results"][f"{HEADLINE:.4f}"], out["halves"][f"{HEADLINE:.4f}"]
    for n in NAMES[1:]:
        per = {"full": useful(hl[n], hl["B0"]), "first_half": useful(hh[n]["first_half"], hh["B0"]["first_half"]),
               "second_half": useful(hh[n]["second_half"], hh["B0"]["second_half"])}
        per["USEFUL"] = all(v["ok"] for v in per.values())
        out["pass_rule"][n] = per
    # bootstrap (headline cost)
    b0 = runs[HEADLINE]["B0"]
    for n in NAMES[1:]:
        s = runs[HEADLINE][n]
        yrs_full = bt.years_between(s["date"])
        out["bootstrap"][n] = {f"block{blk}": bt.block_bootstrap(s["ret"].to_numpy(), b0["ret"].to_numpy(), yrs_full, block=blk)
                               for blk in (63, 21)}
    # after-tax (S1, S2 + B0), each cost, with and without the Rs 1.25 lakh yearly exemption
    for c in bt.COSTS:
        t = {"B0": {"no_exemption": bt.after_tax_buyhold(runs[c]["B0"]), "with_1.25L_exemption": bt.after_tax_buyhold(runs[c]["B0"], 125_000)}}
        for n in ("S1", "S2"):
            t[n] = {"no_exemption": bt.after_tax(runs[c][n]), "with_1.25L_exemption": bt.after_tax(runs[c][n], 125_000)}
        out["tax"][f"{c:.4f}"] = t
    if not a.no_controls:
        ctl = {}
        for n in ("S1", "S2"):  # +1 day extra delay (a real effect weakens gradually; a leak collapses)
            ctl[f"{n}_extra_delay_1d"] = bt.metrics(bt.run(df, sig[n].shift(1), HEADLINE, start=start + 1))
            ctl[f"{n}_extra_delay_5d"] = bt.metrics(bt.run(df, sig[n].shift(5), HEADLINE, start=start + 5))
        ctl["S3_extra_delay_1d"] = bt.metrics(bt.run(df, sig["S3"].shift(1), HEADLINE, start=start + 1))
        peek = ((df["close"] / df["open"]).shift(-1) > 1).astype(float)
        peek.iloc[-1] = 0.0
        ctl["LEAKY_peek_next_day"] = bt.metrics(bt.run(df, peek, HEADLINE, start=start))
        ctl["placebo_S1"] = placebo(df, sig["S1"], start)
        ctl["placebo_S2"] = placebo(df, sig["S2"], start)
        out["controls"] = ctl
    # ledger (own file) : one row per strategy, plus a hash of the code that produced the numbers
    code_hash = hashlib.sha256((HERE / "backtest.py").read_bytes() + (HERE.parent / "candidate.py").read_bytes()).hexdigest()[:12]
    with LEDGER.open("a") as fh:
        for n in NAMES:
            fh.write(json.dumps({"t": time.time(), "strategy": n, "code_hash": code_hash, "cagr_025": hl[n]["cagr"], "max_dd_025": hl[n]["max_dd"],
                                 "useful": out["pass_rule"].get(n, {}).get("USEFUL")}) + "\n")
    OUT.mkdir(exist_ok=True)
    (OUT / "lowturn_results.json").write_text(json.dumps(out, indent=2))
    write_tables(out, yrs)
    print(json.dumps(out, indent=2))


def write_tables(o: dict, yrs: pd.DataFrame) -> None:
    L = ["# Low-turnover NIFTY results (DEV data, price index, cash 6.5%)", "",
         f"Evaluated {o['data']['eval_first_decision']} .. {o['data']['last']} ({o['data']['bars']} bars loaded). Price index: dividends excluded.", ""]
    for c, res in o["results"].items():
        L += [f"## Cost per one-way trade {float(c)*100:.2f}%", "", "| | CAGR | Vol | MaxDD | Sharpe | Calmar | %Invested | Switches/yr | Worst yr |", "|---|---|---|---|---|---|---|---|---|"]
        for n, m in res.items():
            L.append(f"| {n} | {pct(m['cagr'])} | {pct(m['vol'])} | {pct(m['max_dd'])} | {m['sharpe']:.2f} | {m['calmar']:.2f} | {pct(m['pct_invested'])} | {m['switches_per_year']:.2f} | {pct(m['worst_year'])} ({m['worst_year_which']}) |")
        for half in ("first_half", "second_half"):
            d = o["halves"][c]["B0"][half + "_dates"]
            L += ["", f"**{half.replace('_', ' ')}** ({d[0]} .. {d[1]})", "", "| | CAGR | Vol | MaxDD | Sharpe | Calmar | %Invested | Switches/yr |", "|---|---|---|---|---|---|---|---|"]
            for n in NAMES:
                m = o["halves"][c][n][half]
                L.append(f"| {n} | {pct(m['cagr'])} | {pct(m['vol'])} | {pct(m['max_dd'])} | {m['sharpe']:.2f} | {m['calmar']:.2f} | {pct(m['pct_invested'])} | {m['switches_per_year']:.2f} |")
        L.append("")
    L += ["## Calendar-year returns at 0.25% cost (first and last years are partial)", "", "| Year | B0 | S1 | S2 | S3 |", "|---|---|---|---|---|"]
    for y, row in yrs.iterrows():
        L.append(f"| {y} | " + " | ".join(pct(row[n]) for n in NAMES) + " |")
    (OUT / "lowturn_results.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
