"""Hostile self-review of B7-01 (adversarial-review skill). Run AFTER crypto_run.py; prints one block per checklist item and writes results/crypto_review.txt.
These are diagnostics on the SAME rule, not new trials: nothing here changes the verdict or is used to pick a setting.
  python research/crypto/crypto_review.py"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crypto_core as cc  # noqa: E402

OUT = HERE / "results"
RETAIL = "count_long_short_ratio"


def pct(x):
    return f"{x * 100:+.3f}%"


def main() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        res = json.loads((OUT / "crypto_results.json").read_text())
        vals, why, qa = cc.load_signal_columns("BTCUSDT")
        opens = cc.load_opens("BTCUSDT")
        first = vals.index.min().date()
        x = np.log(vals[RETAIL])
        z = cc.zscores(x)
        run = cc.build_trades(z, opens, first)
        t = run.trades
        net = (t["direction"] * t["gross"] - cc.COST).to_numpy()

        print("1. LOOKAHEAD")
        # (a) every trade enters strictly after its 23:50 signal stamp: entry = D+1 00:00, signal row = D 23:50 -> 10 minutes of slack, no overlap in time.
        gap = (t["entry"] - (t["signal_date"] + pd.Timedelta(hours=23, minutes=50))).unique()
        print(f"   entry minus signal stamp (should be 10 minutes only): {[str(g) for g in gap]}")
        # (b) one extra day of delay: a real, slow crowd effect weakens gradually; a leak would collapse or flip
        zl = z.copy()
        zl.index = zl.index + pd.Timedelta(days=1)
        rl = cc.build_trades(zl, opens, first)
        sl = cc.stats(rl, with_null=False)
        print(f"   signal delayed by one extra day: n {sl['n_trades']}, mean net {pct(sl['mean_net'])}, zero-cost {pct(sl['mean_zero_cost'])} "
              f"(headline {pct(res['symbols']['BTCUSDT']['headline']['mean_net'])} / {pct(res['symbols']['BTCUSDT']['headline']['mean_zero_cost'])})")
        print("   the 23:50 stamp: whether Binance stamps the START or END of the 5-minute window is NOT verified. If it is the END of the window the 23:50 row is complete by 23:50"
              " (safe); if it is the START, the row covers 23:50-23:55 and the entry at 00:00 is still after it. Either way the entry is at or after the row's whole window.")

        print("2. LEAKAGE: no 2026 file on disk:", not any(p.name >= "BTCUSDT-metrics-2026" for p in (cc.DATA / "parsed" / "metrics" / "BTCUSDT").glob("*.csv")),
              "| last metrics date", vals.index.max().date(), "| last kline bar", opens.index.max())

        print("3. TRIALS: one pre-registered trial (B7-01, trial 17 overall). ETH and the information-only runs are not trials and not used for the verdict. alpha =", f"{cc.ALPHA:.5f}",
              "| the loop ledger holds 16 trials before this one (not touched here)")

        print("4. CONTROLS")
        h = res["symbols"]["BTCUSDT"]["headline"]
        print(f"   random-entry null p {h['null_p']:.4f} (null mean {pct(h['null_mean'])}, null 95th pct {pct(h['null_q95'])}); bootstrap p {h['boot_p']:.4f}; "
              f"opposite direction mean net {pct(res['information_only']['opposite_follow_crowd']['mean_net'])} (zero cost {pct(res['information_only']['opposite_follow_crowd']['mean_zero_cost'])})")
        print(f"   independent days: trades are daily and can chain, so adjacent trades share a price (exit of one = entry of the next); blocks of 5 handle some of that. n = {len(t)}")

        print("5. COSTS (0.12% per round trip; funding NOT modelled)")
        for c in (0.0, 0.0012, 0.002, 0.003, 0.005):
            n_ = (t["direction"] * t["gross"] - c)
            print(f"   cost {c * 100:.2f}%: mean net {pct(n_.mean())}")
        gross_mean = (t["direction"] * t["gross"]).mean()
        print(f"   break-even round-trip cost {gross_mean * 100:.3f}% (the rule assumes 0.12%)")
        print("   funding (information): ", json.dumps(res["information_only"]["funding_btc"], default=str))

        print("6. FILLS: entry/exit at the OPEN price of a daily candle with 0.02% slippage assumed; no order-book data; BTC perpetual is very liquid but a 00:00 UTC open"
              " print is a single instant (funding settles at 00:00/08:00/16:00 UTC and spreads can widen). No liquidation / leverage is modelled.")

        print("7. SELECTION / SKIPS")
        sk = res["symbols"]["BTCUSDT"]["headline"]["skips"]
        print("   day statuses:", sk, "| days without a retail x:", res["symbols"]["BTCUSDT"]["data_qa"]["days_without_retail_x"],
              "| missing metrics files:", len(res["symbols"]["BTCUSDT"]["data_qa"]["missing_days"]))
        status = run.days.set_index(pd.to_datetime(run.days["date"]))["status"]
        mv = (opens.shift(-2) / opens.shift(-1) - 1).reindex(status.index)  # the move of the day that would be traded (open D+1 -> open D+2)
        tm = mv[status == "traded"].abs().mean()
        sm = mv[status.isin(["flat", "overlap"])].abs().mean()
        print(f"   mean |day move|: traded days {tm * 100:.2f}% vs flat days {sm * 100:.2f}% (a signal that picks big-move days is not an edge by itself)")

        print("8. REGIME / CONCENTRATION")
        for r in h["by_year"]:
            print(f"   {r['year']}: n {r['n']} (L {r['n_long']} / S {r['n_short']}) mean net {pct(r['mean_net'])}  total {pct(r['total_net'])}  worst {pct(r['worst'])}  maxDD {r['max_drawdown_in_year'] * 100:.1f}pp")
        order = np.sort(net)
        print(f"   best trade {pct(order[-1])}, top 3 sum {pct(order[-3:].sum())} vs total {pct(net.sum())}; mean without best trade {pct((net.sum() - order[-1]) / (len(net) - 1))}; "
              f"mean without best 3 {pct((net.sum() - order[-3:].sum()) / (len(net) - 3))}; without worst 3 {pct((net.sum() - order[:3].sum()) / (len(net) - 3))}")
        for d, name in ((1, "LONG (crowd short)"), (-1, "SHORT (crowd long)")):
            m = net[(t["direction"] == d).to_numpy()]
            print(f"   {name}: n {len(m)}, mean net {pct(m.mean()) if len(m) else 'n/a'}")
        bear = (opens.index >= "2022-01-01") & (opens.index < "2023-01-01")
        print(f"   BTC open 2022-01-01 to 2022-12-31: {opens[bear].iloc[0]:.0f} -> {opens[bear].iloc[-1]:.0f}; whole sample first {opens.iloc[0]:.0f} last {opens.iloc[-1]:.0f} (a long-biased drift matters for the L/S mix)")

        print("9. ARITHMETIC: five trades recomputed from the raw monthly kline file text")
        sample = t.iloc[np.linspace(0, len(t) - 1, 5).astype(int)]
        for _, r in sample.iterrows():
            e, xx = opens[r["entry"]], opens[r["exit"]]
            print(f"   signal {r['signal_date'].date()} z {r['z']:+.2f} dir {int(r['direction']):+d}: open {e:.2f} -> {xx:.2f}, gross {pct(xx / e - 1)}, net {pct(r['direction'] * (xx / e - 1) - cc.COST)} (engine {pct(r['net'])})")
        again = cc.stats(run)
        print(f"   re-run of the statistics gives identical numbers: boot p {again['boot_p'] == h['boot_p']}, null p {again['null_p'] == h['null_p']}")

        print("10. PLAUSIBILITY: crowd retail long/short ratio vs the day's own move")
        mv_d = (opens.shift(-1) / opens - 1).reindex(z.index)
        ok = z["z"].notna() & mv_d.notna()
        print(f"   correlation of z with the move OPEN(D)->OPEN(D+1) (the day the ratio was measured on): {np.corrcoef(z['z'][ok], mv_d[ok])[0, 1]:+.3f} (descriptive; the stamp is 23:50 of that day)")
        mv_n = (opens.shift(-2) / opens.shift(-1) - 1).reindex(z.index)
        ok = z["z"].notna() & mv_n.notna()
        print(f"   correlation of z with the NEXT day's move (the traded day): {np.corrcoef(z['z'][ok], mv_n[ok])[0, 1]:+.3f}")
        print(f"   mean win rate {h['win_rate'] * 100:.1f}%")
    text = buf.getvalue()
    (OUT / "crypto_review.txt").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
