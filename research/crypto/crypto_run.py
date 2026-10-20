"""Run the pre-registered study ONCE (docs/ideas/IDEAS_BATCH7_CRYPTO_CROWD_2026-10-20.md): trial B7-01 on BTCUSDT, the ETHUSDT confirmation, and the listed
information-only checks. No arguments: nothing can be tuned from the command line. Writes research/crypto/results/crypto_results.json (+ .md tables).
Does NOT touch research/ideas/loop/ledger_loop.jsonl (the project manager records B7-01 there after merging).
  python research/crypto/crypto_run.py"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crypto_core as cc  # noqa: E402

OUT = HERE / "results"
RETAIL, TOP = "count_long_short_ratio", "count_toptrader_long_short_ratio"


def code_hash() -> str:
    h = hashlib.sha256()
    for f in ("crypto_core.py", "crypto_run.py", "crypto_fetch.py"):
        h.update((HERE / f).read_bytes())
    return h.hexdigest()[:16]


def data_qa(sym: str, vals: pd.DataFrame, why: pd.DataFrame, qa: pd.DataFrame) -> dict:
    first = vals.index.min().date()
    expected = pd.date_range(first, cc.LAST_DEV, freq="D")
    have = set(vals.index)
    missing = [str(d.date()) for d in expected if d not in have]
    short = qa[~qa["full_day"]]
    return {"symbol": sym, "first_date": str(first), "last_date": str(vals.index.max().date()), "expected_days": len(expected), "files": len(vals), "missing_days": missing,
            "raw_rows": int(qa["raw_rows"].sum()), "unique_rows": int(qa["unique_rows"].sum()), "dup_rows": int(qa["dup_rows"].sum()),
            "days_with_duplicates": int((qa["dup_rows"] > 0).sum()), "dup_conflicts": int(qa["dup_conflicts"].sum()),
            "days_not_full_288": [{"date": str(r["date"]), "unique": int(r["n_unique"]), "off_day": int(r["off_day"]), "off_grid": int(r["off_grid"]),
                                   "first": r["first"], "last": r["last"]} for _, r in short.iterrows()],
            "days_with_off_day_stamps": int((qa["off_day"] > 0).sum()), "days_with_off_grid_stamps": int((qa["off_grid"] > 0).sum()),
            "skip_reasons_retail_2350": {k: int(v) for k, v in why[RETAIL].value_counts(dropna=True).items()},
            "days_without_retail_x": int(vals[RETAIL].isna().sum()), "days_without_top_x": int(vals[TOP].isna().sum())}


def load_funding(sym: str) -> pd.DataFrame:
    base = cc.DATA / "parsed" / "funding" / sym
    files = sorted(base.glob("*.csv"))
    if not files:
        return pd.DataFrame(columns=["t", "rate"])
    parts = []
    for f in files:
        raw = pd.read_csv(f)
        t = pd.to_numeric(raw["calc_time"]).astype("int64")
        parts.append(pd.DataFrame({"t": pd.to_datetime(t.values, unit="us" if t.max() > 1e14 else "ms"), "rate": pd.to_numeric(raw["last_funding_rate"]).values}))
    f = pd.concat(parts).drop_duplicates("t").sort_values("t").reset_index(drop=True)
    if len(f) and f["t"].max() >= cc.FIRST_HOLDOUT:
        raise RuntimeError("funding data at or after 2026-01-01 present")
    return f


def funding_info(f: pd.DataFrame, run: cc.Run) -> dict:
    """Information only. Average funding rate over the sample, and what funding would have done to the trades (long pays +rate, short receives it)."""
    if f.empty:
        return {"available": False}
    f = f[f["t"] >= pd.Timestamp(run.window[0])]  # only the study window (from the symbol's first metrics date)
    out = {"available": True, "n_payments": len(f), "first": str(f["t"].min()), "last": str(f["t"].max()), "mean_rate_per_payment": float(f["rate"].mean()),
           "mean_rate_per_day_if_3_payments": float(f["rate"].mean() * 3), "mean_rate_annualised_simple": float(f["rate"].mean() * 3 * 365),
           "share_negative_payments": float((f["rate"] < 0).mean())}
    t = run.trades
    if len(t):
        paid = []
        for _, r in t.iterrows():
            s = f.loc[(f["t"] > r["entry"]) & (f["t"] <= r["exit"]), "rate"].sum()
            paid.append(r["direction"] * s)  # +: the position PAYS funding
        paid = np.array(paid)
        out["mean_funding_paid_per_trade"] = float(paid.mean())
        out["mean_net_after_funding"] = float((t["net"] - paid).mean())
    return out


def verdict(btc: dict, eth: dict) -> tuple:
    a = bool(btc["n_trades"] >= cc.MIN_TRADES)
    b = bool(btc["mean_net"] > 0)
    c = bool(btc["boot_p"] < cc.ALPHA)
    d = bool(btc["first_n"] > 0 and btc["second_n"] > 0 and btc["first_mean"] > 0 and btc["second_mean"] > 0)
    e = bool(btc["null_p"] < cc.ALPHA)
    f = bool(eth["n_trades"] > 0 and eth["mean_net"] > 0)
    checks = {"a_n_ge_100": a, "b_mean_net_positive": b, "c_boot_p": c, "d_both_halves_positive": d, "e_null_p": e, "f_eth_mean_net_positive": f}
    if all(checks.values()):
        return "SURVIVES", checks
    if b and btc["boot_p"] < 0.05:
        return "INCONCLUSIVE", checks
    return "REJECT", checks


def pct(x):
    return "n/a" if x != x else f"{x * 100:+.3f}%"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    res: dict = {"trial": "B7-01", "trial_number_overall": 17, "alpha": cc.ALPHA, "code_hash": code_hash(), "symbols": {}}
    runs: dict = {}
    for sym in ("BTCUSDT", "ETHUSDT"):
        vals, why, qa = cc.load_signal_columns(sym)
        opens = cc.load_opens(sym)
        first = vals.index.min().date()
        x = np.log(vals[RETAIL])
        z = cc.zscores(x)
        run = cc.build_trades(z, opens, first)
        s = cc.stats(run)
        s["skips"] = cc.skip_counts(run)
        s["by_year"] = cc.by_year(run)
        s["z_span_days_max"] = float(z["span_days"].max())
        s["z_span_days_median"] = float(z["span_days"].median())
        s["window"] = [str(first), str(cc.LAST_DEV)]
        res["symbols"][sym] = {"headline": s, "data_qa": data_qa(sym, vals, why, qa), "kline_days": int(len(opens)), "kline_first": str(opens.index.min()), "kline_last": str(opens.index.max())}
        runs[sym] = (vals, opens, x, z, run)
    btc, eth = res["symbols"]["BTCUSDT"]["headline"], res["symbols"]["ETHUSDT"]["headline"]
    res["verdict"], res["checks"] = verdict(btc, eth)

    # ---------------------------------------------------------------- information only (BTC), each run once, nothing else varied
    vals, opens, x, z, run = runs["BTCUSDT"]
    first = vals.index.min().date()
    info: dict = {}
    for thr in (1.0, 2.0):
        r = cc.build_trades(z, opens, first, thr=thr)
        info[f"threshold_{thr}"] = {**cc.stats(r), "skips": cc.skip_counts(r)}
    hourly = cc.load_opens("BTCUSDT", "klines1h")
    r = cc.build_trades(z, hourly, first, hold=timedelta(hours=4))
    info["hold_4h"] = {**cc.stats(r), "skips": cc.skip_counts(r)}
    r = cc.build_trades(z, opens, first, hold=timedelta(days=3))
    info["hold_3d"] = {**cc.stats(r), "skips": cc.skip_counts(r)}
    r = cc.build_trades(z, opens, first, sign=-1)
    info["opposite_follow_crowd"] = {**cc.stats(r), "skips": cc.skip_counts(r)}
    xt = np.log(vals[TOP])
    zt = cc.zscores(xt)
    r = cc.build_trades(zt, opens, first)
    info["top_trader_measure"] = {**cc.stats(r), "skips": cc.skip_counts(r)}
    xs_ = x - xt
    zs = cc.zscores(xs_)
    r = cc.build_trades(zs, opens, first)
    info["retail_minus_top_spread"] = {**cc.stats(r), "skips": cc.skip_counts(r)}
    info["funding_btc"] = funding_info(load_funding("BTCUSDT"), run)
    info["funding_eth"] = funding_info(load_funding("ETHUSDT"), runs["ETHUSDT"][4])
    res["information_only"] = info

    # ---------------------------------------------------------------- write
    # save the trades so the plain-CSV crosscheck can compare them one by one
    for sym in ("BTCUSDT", "ETHUSDT"):
        t = runs[sym][4].trades.copy()
        for c in ("signal_date", "entry", "exit"):
            t[c] = t[c].astype(str)
        t.to_csv(OUT / f"trades_{sym}.csv", index=False)
        runs[sym][4].days.to_csv(OUT / f"days_{sym}.csv", index=False)
        pd.DataFrame({"x_retail": runs[sym][2], "z": runs[sym][3]["z"], "status": runs[sym][3]["status"]}).to_csv(OUT / f"signals_{sym}.csv")
    (OUT / "crypto_results.json").write_text(json.dumps(res, indent=1, default=str))

    L = ["| Run | Trades (L/S) | Mean net | Zero cost | Boot p | Null p | First half (n, mean) | Second half (n, mean) | Worst | Max DD |", "|---|---|---|---|---|---|---|---|---|---|"]

    def row(name, s, null=True):
        return (f"| {name} | {s['n_trades']} ({s['n_long']}/{s['n_short']}) | {pct(s['mean_net'])} | {pct(s['mean_zero_cost'])} | {s['boot_p']:.4f} | "
                f"{s['null_p']:.4f} | {s.get('first_n')}, {pct(s.get('first_mean', float('nan')))} | {s.get('second_n')}, {pct(s.get('second_mean', float('nan')))} | "
                f"{pct(s['worst_trade'])} | {s['max_drawdown'] * 100:.1f} pp |")

    L.append(row("B7-01 BTCUSDT", btc))
    L.append(row("ETH confirmation", eth))
    for k, v in info.items():
        if k.startswith("funding"):
            continue
        L.append(row(k, v))
    (OUT / "crypto_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print("\nverdict:", res["verdict"], res["checks"])
    for sym in ("BTCUSDT", "ETHUSDT"):
        print(sym, "skips", res["symbols"][sym]["headline"]["skips"])
    print("funding:", json.dumps(info["funding_btc"], default=str))


if __name__ == "__main__":
    main()
