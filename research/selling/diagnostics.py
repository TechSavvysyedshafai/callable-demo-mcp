"""SELL1 diagnostics (controls on the two pre-registered variants; NOT extra strategy trials; none feeds the pass rule).
  python diagnostics.py   -> results/diagnostics.json
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import backtest as bt  # noqa: E402
import evaluate as ev  # noqa: E402


def stats(weeks):
    s = ev.summarize(weeks)
    return {k: (round(v, 1) if isinstance(v, float) else v) for k, v in s.items() if k in
            ("weeks_traded", "weeks_skipped", "win_rate", "mean_net", "median_net", "total_net", "worst_week", "max_drawdown", "ci90_lo", "ci90_hi", "breach_rate")}


out = {}
for v in ("V1", "V2"):
    base = bt.run_all(v, 0.20)
    d = {"base": stats(base)}
    # lookahead controls: delay entry by 1 and 2 bars (a leak would collapse or flip; a real effect weakens gradually)
    d["entry_shift_+1_bar"] = stats(bt.run_all(v, 0.20, shift=1))
    d["entry_shift_+2_bars"] = stats(bt.run_all(v, 0.20, shift=2))
    # same-week comparison: base restricted to the weeks that the shifted runs could price (strikes unchanged, so files exist)
    for key, kw in (("entry_shift_+1_bar", {"shift": 1}), ("entry_shift_+2_bars", {"shift": 2}), ("strikes_from_previous_bar_close", {"spot_shift": -1})):
        keep = {w.expiry for w in bt.run_all(v, 0.20, **kw) if w.skipped is None}
        sub = [w for w in base if w.expiry in keep]
        d[key + "__base_on_same_weeks"] = {"n": len(sub), "mean_net": round(float(np.mean([w.net_rs for w in sub])), 1), "total_net": round(sum(w.net_rs for w in sub), 1)}
    # strike spot taken from the PREVIOUS bar's close (fully causal at the 09:30 fill)
    d["strikes_from_previous_bar_close"] = stats(bt.run_all(v, 0.20, spot_shift=-1))
    tr = [w for w in base if w.skipped is None]
    h = len(tr) // 2
    d["first_half"] = stats(tr[:h]) if False else {"n": h, "total_net": round(sum(w.net_rs for w in tr[:h]), 1), "mean_net": round(float(np.mean([w.net_rs for w in tr[:h]])), 1)}
    d["second_half"] = {"n": len(tr) - h, "total_net": round(sum(w.net_rs for w in tr[h:]), 1), "mean_net": round(float(np.mean([w.net_rs for w in tr[h:]])), 1)}
    # period-correct statutory rates for Oct 2024 - Mar 2026 (STT 0.10% on premium, 0.125% on exercise): COST sensitivity, kinder than the brief
    bt.SETTLE_STT = 0.00125
    d["lower_stt_0.10_and_0.125"] = stats(bt.run_all(v, 0.20, cm_kwargs={"stt_sell_pct": 0.001}))
    bt.SETTLE_STT = 0.0015
    # gross before any fee or slippage: mean of (credit - payout) in rupees at slippage 0
    w0 = bt.run_all(v, 0.0)
    d["gross_rs_mean_zero_slippage_zero_fees"] = round(float(np.mean([w.gross_pts * bt.LOT for w in w0 if w.skipped is None])), 1)
    d["mean_credit_pts_zero_slippage"] = round(float(np.mean([w.credit for w in w0 if w.skipped is None])), 2)
    d["mean_payout_pts_zero_slippage"] = round(float(np.mean([w.credit - w.gross_pts for w in w0 if w.skipped is None])), 2)
    if v == "V2":
        st = [w for w in tr if w.stopped]
        ns = [w for w in tr if not w.stopped]
        d["stopped_weeks"] = {"n": len(st), "mean_net": round(float(np.mean([w.net_rs for w in st])), 1), "worst": round(min(w.net_rs for w in st), 1),
                              "of_which_would_have_expired_worthless_or_profitable_under_V1": None}
        v1 = {w.expiry: w for w in bt.run_all("V1", 0.20)}
        d["stopped_weeks"]["of_which_would_have_expired_worthless_or_profitable_under_V1"] = sum(1 for w in st if v1[w.expiry].net_rs > 0)
        d["stopped_weeks"]["v1_mean_net_same_weeks"] = round(float(np.mean([v1[w.expiry].net_rs for w in st])), 1)
    out[v] = d
(HERE / "results" / "diagnostics.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
