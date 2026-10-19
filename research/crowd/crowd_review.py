"""Hostile self-review of B5-01 (skill adversarial-review). INFORMATION ONLY: nothing here is a trial, nothing changes the verdict, no threshold or rule is varied.
  python research/crowd/crowd_review.py     (run after crowd_run.py)       Writes results/crowd_review.txt"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crowd_core as cc  # noqa: E402

OUT = HERE / "results"


def main() -> None:
    L: list = []
    P = L.append
    res = json.loads((OUT / "crowd_results.json").read_text())
    bars, closes, expiries = cc.wc.load_index()
    by_ts = bars.set_index("date")
    plans = cc.make_plans(bars, expiries)
    loader = cc.file_loader()
    sig = cc.signal_weeks(plans, loader)
    tr = cc.build_trades(plans, sig, by_ts, closes)
    trades = tr["trades"]
    net = np.array([t["net_ret"] for t in trades])

    # 1. Lookahead
    def trunc_loader(ex, k, kind):
        f = loader(ex, k, kind)
        if f is None:
            return None
        d = next(p["entry_day"] for p in plans if p["expiry"] == ex)
        return f[f.index <= pd.Timestamp(f"{d} 09:25")]
    sig_t = cc.signal_weeks(plans, trunc_loader)
    same = all((a["x"] == b["x"]) and (a["direction"] == b["direction"]) for a, b in zip(sig, sig_t))
    P(f"1. Lookahead: signals recomputed from option candles CUT at 09:25 of the entry day are identical to the full-file signals: {same}. Entry price is the open of the 09:30 bar, "
      f"which is the first price after the 09:25 bar closes. Index S = close of the 09:25 bar. Entry shifted +1 / +2 bars: mean net {res['info']['entry_plus_1_bar']['mean_net'] * 100:+.3f}% / "
      f"{res['info']['entry_plus_2_bar']['mean_net'] * 100:+.3f}% (base {res['primary']['mean_net'] * 100:+.3f}%). Inherited weakness: S and the OI are read from the bar that ENDS at 09:30, "
      f"the same instant as the entry open; real OI is published with a delay (unverified: see the report).")
    # staleness of OI at 09:25: equal to the last OI of the previous trading day?
    stale = tot = 0
    for p in plans:
        if p["skipped"] is not None:
            continue
        for kk in cc.strike_grid(p["spot"]):
            for kind in ("CE", "PE"):
                f = loader(p["expiry"], kk, kind)
                if f is None or p["sig_ts"] not in f.index:
                    continue
                prev = f[f.index < pd.Timestamp(f"{p['entry_day']} 09:00")]
                if prev.empty:
                    continue
                tot += 1
                stale += int(float(f.loc[p["sig_ts"], "oi"]) == float(prev["oi"].iloc[-1]))
    P(f"   OI freshness: at 09:25 the OI equals the previous day's last OI for {stale} of {tot} strike legs ({stale / max(tot, 1) * 100:.1f}%): "
      "a high share would mean OI is only refreshed end of day, so 'OI at 09:25' would really be 'OI at yesterday's close'.")

    # 2. Leakage
    P(f"2. Leakage: index data end {bars['date'].max()} (dev cutoff {cc.DEV_CUTOFF}); the holdout folder is never opened (a test greps the source); the 2026-04-21 expiry is excluded.")
    # 3. Trials
    P(f"3. Trials: exactly one trial (B5-01, trial {cc.TOTAL_TRIALS}, alpha {cc.ALPHA:.5f}). The opposite direction, the +/-150 window, the entry shifts and the zero-cost line are information only. "
      "The run script takes no arguments and was run once on the final data; the pre-registration was committed (4fae7b2) before any option file existed.")
    # 4. Controls
    cand = np.array(tr["cand"])
    n_long = sum(t["direction"] > 0 for t in trades)
    n_short = len(trades) - n_long
    P(f"4. Controls: random-entry null p {res['primary']['null_p']:.4f} (null mean {res['primary'].get('null_mean', float('nan')) * 100:+.3f}%, 95th pct {res['primary'].get('null_q95', float('nan')) * 100:+.3f}%). "
      f"Placebo/drift: the eligible weeks ({len(cand)}) return {cand.mean() * 100:+.3f}% a week on average (long-only drift); the trades are {n_long} long / {n_short} short, so the net "
      f"exposure is {(n_long - n_short) / max(len(trades), 1) * 100:+.0f}% long. Always-long over the eligible weeks: mean net {(cand.mean() - cc.COST) * 100:+.3f}%; always-short: {(-cand.mean() - cc.COST) * 100:+.3f}%.")
    # 5. Costs
    P(f"5. Costs: 0.10% per round trip on notional is assumed to cover a futures proxy (no brokerage per order, no slippage sweep: the index has no bid/ask here). Mean at zero cost "
      f"{res['primary']['mean_zero_cost'] * 100:+.3f}% vs net {res['primary']['mean_net'] * 100:+.3f}%: break-even round-trip cost = {res['primary']['mean_zero_cost'] * 100:.3f}%. "
      "A weekly hold of a futures contract costs far less than 0.10%, so the cost is not what decides the answer.")
    P("6. Fills: entry at the OPEN of the 09:30 index bar and exit at the official close are index levels, not futures prices (no basis, no roll, no bid/ask). Nothing here is tradeable as-is; "
      "an index open is not a fill price for anyone.")
    # 7. Selection / skips
    sk = res["skips"]
    P(f"7. Selection: {sk['n_skipped']} of {sk['n_weeks']} weeks have no z: " + "; ".join(f"{k}: {v['n']} ({', '.join(v['weeks'][:4])}{'...' if v['n'] > 4 else ''})" for k, v in sk["by_reason"].items())
      + f". Weeks with an x but fewer than 9 strikes: {res['coverage']['weeks_with_fewer_than_9_strikes'] or 'none'}; strikes used min/median/max "
        f"{res['coverage']['strikes_used_min']}/{res['coverage']['strikes_used_median']}/{res['coverage']['strikes_used_max']}.")
    # 8. Regime
    if trades:
        df = pd.DataFrame(trades)
        df["entry_day"] = pd.to_datetime(df["entry_day"])
        df["q"] = df["entry_day"].dt.to_period("Q").astype(str)
        P("8. Regime: mean net by calendar quarter (n): " + "; ".join(f"{q} {g['net_ret'].mean() * 100:+.2f}% ({len(g)})" for q, g in df.groupby("q")))
        P("   by direction: " + "; ".join(f"{'LONG' if d > 0 else 'SHORT'} n={len(g)} mean {g['net_ret'].mean() * 100:+.3f}%" for d, g in df.groupby("direction")))
        order = np.argsort(-np.abs(net))
        P(f"   concentration: largest 3 trades by |return| sum to {net[order[:3]].sum() * 100:+.2f}% of a total {net.sum() * 100:+.2f}%; mean without the best trade "
          f"{(net.sum() - net.max()) / max(len(net) - 1, 1) * 100:+.3f}%, without the worst {(net.sum() - net.min()) / max(len(net) - 1, 1) * 100:+.3f}%.")
        P(f"   lot size / rule changes inside the window: lot sizes read from Upstox contract lists (expiries per lot size) {res['lot_sizes_from_contract_lists']}; the expiry weekday moved Thu -> Tue "
          "on 2025-09-02 (the entry-day rule follows the calendar file, not a weekday). The rupee figures use 75 units for every trade and are scale only.")
    # 9. Arithmetic
    P("9. Arithmetic: reproduced by research/crowd/crowd_crosscheck.py (standard csv module only, no shared code): see results/crowd_crosscheck.txt.")
    # 10. Plausibility + signal anatomy (exploratory, not tested)
    x = np.array([s["x"] for s in sig if s["x"] is not None])
    z = np.array([s["z"] for s in sig if s["z"] is not None])
    ret_prev = []
    for s in sig:
        if s["z"] is None:
            continue
        i = s["k"]
        ret_prev.append(closes[expiries[i - 1]] / bars.set_index("date").loc[plans[i]["sig_ts"], "close"] - 1 if i > 0 else np.nan)
    rp = np.array(ret_prev, float)
    ok = ~np.isnan(rp)
    corr = float(np.corrcoef(rp[ok], z[ok])[0, 1]) if ok.sum() > 3 else float("nan")
    P(f"10. Plausibility: PCR x mean {x.mean():+.3f}, sd {x.std(ddof=1):.3f} over {len(x)} weeks; z has {len(z)} values, {int((np.abs(z) >= 1).sum())} with |z| >= 1 "
      f"(trades), {int(((np.abs(z) >= 0.9) & (np.abs(z) < 1)).sum())} within 0.1 below the threshold and {int(((np.abs(z) >= 1) & (np.abs(z) < 1.1)).sum())} within 0.1 above it. "
      f"Correlation of z with the previous week's index move (expiry close to this entry): {corr:+.2f} (is the 'crowd' signal just last week's price move?). "
      f"Hit rate {res['primary'].get('win_rate', float('nan')) * 100:.0f}%. With about {len(trades)} trades in 80 weeks one regime can decide everything; 80 weeks cannot show crash risk.")
    # independent bootstrap check of the p-value arithmetic (plain numpy, same recipe, different code)
    if len(net) >= 3:
        rng = np.random.default_rng(cc.fi.SEED)
        m, b = len(net), min(3, len(net))
        k = int(np.ceil(m / b))
        starts = rng.integers(0, m - b + 1, size=(10_000, k))
        idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(10_000, -1)[:, :m]
        means = net[idx].mean(axis=1) - net.mean()
        p2 = (1 + np.sum(means >= net.mean())) / 10_001
        P(f"    Bootstrap p re-derived with an independent loop: {p2:.4f} vs engine {res['primary']['boot_p']:.4f}.")
    P(f"Verdict of the review: see the report; engine verdict {res['primary']['verdict']}, checks {res['primary']['checks']}.")
    (OUT / "crowd_review.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
