"""TAIL STRESS for SELL1 -- MODEL-BASED and INFORMATIONAL ONLY (it cannot change the pre-registered pass rule).

For every historical week in the long daily NIFTY history (2000 to the dev cut-off) with an India VIX reading, build the same
percentage-rule condor (short strikes +/-1.2%, wings = 150 / median real entry spot as a % of spot, NOT rounded to 50), credit from
Black-Scholes at the prior-day VIX close, scaled by a CALIBRATION RATIO = real fill credit / Black-Scholes credit measured on the
real-price sample. Entry = open of the trading day nearest on-or-before each Thursday; expiry = close of the same day a week later.

  python stress.py --fetch    # downloads India VIX daily history (dev only, to the cut-off) to research/data/india_vix_long_dev.csv
  python stress.py            # needs data/nifty_day_long_dev.csv (lowturn/fetch_long_daily.py) and the real option files
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "upstox"), str(HERE.parent / "scalp" / "options")]
import backtest as bt  # noqa: E402
from bs import price as bs_price  # noqa: E402
from costs_opt import OptionCostModel  # noqa: E402

R = 0.065
SHORT_PCT = 0.012
VIX_FILE = bt.DATA / "india_vix_long_dev.csv"


def fetch_vix():
    import upstox_api as u
    v = u.historical(u.INDIA_VIX, "days", 1, date(2000, 1, 1), bt.DEV_CUTOFF)  # end = dev cut-off: no holdout dates requested
    v["date"] = v["date"].dt.normalize()
    v[["date", "close"]].to_csv(VIX_FILE, index=False)
    print(f"India VIX: {len(v)} days {v['date'].min().date()} .. {v['date'].max().date()} -> {VIX_FILE}")


def bs_condor(spot, sc, lc, sp, lp, T, iv):
    p = {n: bs_price(spot, k, T, iv, is_call) for n, k, is_call in (("sc", sc, True), ("lc", lc, True), ("sp", sp, False), ("lp", lp, False))}
    return p["sc"] + p["sp"] - p["lc"] - p["lp"], p


def prior_vix(vix: pd.Series, d: pd.Timestamp):
    s = vix[vix.index < d]
    return float(s.iloc[-1]) / 100 if len(s) else None


def calibration(vix: pd.Series):
    """Real fill credit (slippage Rs0.20, V1) / Black-Scholes credit at the prior-day VIX, for each traded real week."""
    rows = []
    for w in bt.run_all("V1", 0.20):
        if w.skipped:
            continue
        iv = prior_vix(vix, pd.Timestamp(w.entry_ts.date()))
        if iv is None:
            continue
        T = (w.expiry - w.entry_ts.date()).days / 365
        st = {k: v[0] for k, v in w.strikes.items()}
        model, _ = bs_condor(w.spot, st["sc"], st["lc"], st["sp"], st["lp"], T, iv)
        rows.append({"expiry": w.expiry.isoformat(), "vix": iv * 100, "real": w.credit, "bs": model, "ratio": w.credit / model, "spot": w.spot})
    return pd.DataFrame(rows)


def thursday_weeks(daily: pd.DataFrame, first: pd.Timestamp):
    days = daily["date"].tolist()
    dset = pd.Series(days)
    t = first + pd.Timedelta(days=(3 - first.weekday()) % 7)
    end = daily["date"].max()
    while t + pd.Timedelta(days=7) <= end:
        e = dset[dset <= t].iloc[-1]
        x = dset[dset <= t + pd.Timedelta(days=7)].iloc[-1]
        if x > e:
            yield e, x
        t += pd.Timedelta(days=7)


def run_stress(daily, vix, ratio, wing_pct, ref, slip=0.20):
    """Every week is rescaled to a constant notional: prices x (ref / entry spot), so Rs figures from 2009 (NIFTY about 3,000) and 2025
    (about 25,000) are comparable. Black-Scholes is homogeneous in (spot, strike), so this only rescales the points."""
    d = daily.set_index("date")
    cm = OptionCostModel(slippage_rs=slip)
    rows = []
    for e, x in thursday_weeks(daily[daily["date"] > vix.index.min()], vix.index.min()):
        iv = prior_vix(vix, e)
        if iv is None:
            continue
        k = ref / float(d.loc[e, "open"])
        spot = ref
        sc, sp = spot * (1 + SHORT_PCT), spot * (1 - SHORT_PCT)
        wing = ref * wing_pct
        lc, lp = sc + wing, sp - wing
        T = (x - e).days / 365
        credit_bs, p = bs_condor(spot, sc, lc, sp, lp, T, iv)
        credit = ratio * credit_bs
        settle = float(d.loc[x, "close"]) * k
        owed = (max(settle - sc, 0) - max(settle - lc, 0) + max(sp - settle, 0) - max(lp - settle, 0))
        costs = sum(cm.side(max(ratio * p[n], 0.05), bt.LOT, is_buy=n in ("lc", "lp")) for n in bt.LEGS)
        costs += bt.SETTLE_STT * bt.LOT * (max(settle - sc, 0) + max(settle - lc, 0) + max(sp - settle, 0) + max(lp - settle, 0))
        net = (credit - owed) * bt.LOT - costs
        rows.append({"entry": e.date().isoformat(), "expiry": x.date().isoformat(), "spot": float(d.loc[e, "open"]), "vix": iv * 100, "move_pct": 100 * (settle / spot - 1),
                     "credit_pts": credit, "owed_pts": owed, "full_width": bool(settle >= lc or settle <= lp), "net_rs": net, "width_pts": wing})
    return pd.DataFrame(rows)


def describe(df):
    x = df["net_rs"].to_numpy()
    maxloss = (df["width_pts"] - df["credit_pts"]) * bt.LOT
    return {"weeks": len(df), "first": df["entry"].iloc[0], "last": df["expiry"].iloc[-1], "mean": float(x.mean()), "median": float(np.median(x)),
            "total": float(x.sum()), "sd": float(x.std(ddof=1)), "p01": float(np.quantile(x, 0.01)), "p05": float(np.quantile(x, 0.05)), "p95": float(np.quantile(x, 0.95)),
            "win_rate": float((x > 0).mean()), "worst": float(x.min()), "max_drawdown": bt.max_drawdown(x), "full_width_weeks": int(df["full_width"].sum()),
            "weeks_loss_ge_95pct_of_max": int((df["net_rs"] <= -0.95 * maxloss).sum()), "worst10": df.nsmallest(10, "net_rs").to_dict("records")}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--fetch", action="store_true")
    a = a.parse_args()
    if a.fetch:
        return fetch_vix()
    daily = pd.read_csv(bt.DATA / "nifty_day_long_dev.csv", parse_dates=["date"])
    vix = pd.read_csv(VIX_FILE, parse_dates=["date"]).set_index("date")["close"]
    cal = calibration(vix)
    ratio = {"median": float(cal["ratio"].median()), "mean": float(cal["ratio"].mean()), "sd": float(cal["ratio"].std(ddof=1)),
             "p25": float(cal["ratio"].quantile(0.25)), "p75": float(cal["ratio"].quantile(0.75)), "min": float(cal["ratio"].min()),
             "max": float(cal["ratio"].max()), "n": int(len(cal)), "corr_with_vix": float(cal["ratio"].corr(cal["vix"]))}
    ref = float(cal["spot"].median())
    wing_pct = bt.WING / ref
    out = {"calibration": ratio, "wing_pct": wing_pct, "reference_spot": ref, "scenarios": {}}
    for name, r in (("median", ratio["median"]), ("p25", ratio["p25"]), ("p75", ratio["p75"]), ("uncalibrated_1.0", 1.0)):
        df = run_stress(daily, vix, r, wing_pct, ref)
        out["scenarios"][name] = {"ratio": r, **describe(df)}
        if name == "median":
            w = pd.to_datetime(df["entry"])
            covid = df[(w >= "2020-02-15") & (w <= "2020-04-30")]
            out["covid_2020_window_median"] = {"weeks": int(len(covid)), "total": float(covid["net_rs"].sum()), "worst": float(covid["net_rs"].min()),
                                               "full_width_weeks": int(covid["full_width"].sum()), "max_abs_move_pct": float(covid["move_pct"].abs().max())}
            out["largest_weekly_moves_pct"] = df.reindex(df["move_pct"].abs().nlargest(5).index)[["entry", "move_pct", "vix", "net_rs"]].to_dict("records")
            df["year"] = pd.to_datetime(df["entry"]).dt.year
            out["by_year_median"] = {int(y): {"weeks": int(len(g)), "total": float(g["net_rs"].sum()), "worst": float(g["net_rs"].min())} for y, g in df.groupby("year")}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "stress_results.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "scenarios"}, indent=1))
    for k, s in out["scenarios"].items():
        print(k, {kk: (round(vv, 1) if isinstance(vv, float) else vv) for kk, vv in s.items() if kk != "worst10"})
    print("worst10 (median ratio):")
    for r in out["scenarios"]["median"]["worst10"]:
        print("  ", r["entry"], r["expiry"], f"move {r['move_pct']:.1f}% vix {r['vix']:.1f} net Rs{r['net_rs']:,.0f}")


if __name__ == "__main__":
    main()
