"""Turn results/dn_results.json into the markdown tables used in RESULTS.md and the completion message. No analysis here."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "results" / "dn_results.json").read_text())
SLIPS = [f"{s:.1f}" if False else str(s) for s in R["slips"]]


def inr(x):
    return "n/a" if x is None else f"{x:,.0f}"


def main_table():
    lines = ["| Var | Slip | Days traded | Skipped (data) | Win % | Mean/day | Median | Total net | Worst day | Max DD (Rs / % base) | Losing streak | Adj/day | Orders/day | Mean 95% CI (5-day blocks) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in "ABC":
        for s in SLIPS:
            x = R["summary"][v][s]
            if not x.get("traded"):
                lines.append(f"| {v} | {s} | 0 | {sum(x['skipped'].values())} | | | | | | | | | | |")
                continue
            lines.append(f"| {v} | {s} | {x['traded']} | {sum(x['skipped'].values())} | {x['win_rate']*100:.0f} | {inr(x['mean'])} | {inr(x['median'])} | {inr(x['total'])} | "
                         f"{inr(x['worst'])} | {inr(x['max_dd'])} / {x['max_dd_pct']:.1f}% | {x['losing_streak']} | {x['avg_adjust']:.2f} | {x['avg_orders']:.1f} | "
                         f"{inr(x['mean_ci95'][0])} to {inr(x['mean_ci95'][1])} |")
    return "\n".join(lines)


def returns_table():
    lines = ["| Var | Slip | Capital base (Rs) | Net / month on base | Worst / best month | Annualised (simple x12) | Total return over sample | Months |", "|---|---|---|---|---|---|---|---|"]
    for v in "ABC":
        for s in SLIPS:
            x = R["summary"][v][s]
            if not x.get("traded"):
                continue
            lines.append(f"| {v} | {s} | {inr(x['capital'])} | {x['monthly_pct']:.2f}% | {x['monthly_pct_min']:.1f}% / {x['monthly_pct_max']:.1f}% | {x['annual_pct_simple']:.1f}% | {x['total_return_pct']:.1f}% | {x['months']} |")
    return "\n".join(lines)


def reasons_table():
    keys = ["eod", "range_exit", "straddle_stop", "cost_to_cost", "forced_close"]
    lines = ["| Var | Slip | " + " | ".join(keys) + " | Breakout days | Skipped adj. | Skipped exit candles | Forced-close days |", "|---|---|" + "---|" * (len(keys) + 4)]
    for v in "ABC":
        for s in SLIPS:
            x = R["summary"][v][s]
            if not x.get("traded"):
                continue
            er = x["end_reasons"]
            lines.append(f"| {v} | {s} | " + " | ".join(f"{er.get(k, 0)*100:.0f}%" for k in keys) + f" | {x['breakout_days']} | {x['skipped_adjust']} | {x['skipped_exit']} | {x['forced_close_days']} |")
    return "\n".join(lines)


def dte_table(slip="0.2"):
    lines = [f"| Var | DTE | Days | Mean net | Total net | Win % | Worst |", "|---|---|---|---|---|---|---|"]
    for v in "ABC":
        for b, d in R["dte"][v][slip].items():
            wr = "" if d["win_rate"] is None else f"{d['win_rate']*100:.0f}"
            lines.append(f"| {v} | {b} | {d['days']} | {inr(d['mean'])} | {inr(d['total'])} | {wr} | {inr(d['worst'])} |")
    return "\n".join(lines)


def skips_table():
    lines = ["| Var | Slip | No swing range (rule failed) | Data skips (reason: days) |", "|---|---|---|---|"]
    for v in "ABC":
        for s in SLIPS:
            x = R["summary"][v][s]
            lines.append(f"| {v} | {s} | {sum(x['no_signal'].values())} {x['no_signal']} | {x['skipped']} |")
    return "\n".join(lines)


def pass_table():
    lines = ["| Var | (a) mean>0 and CI low>0 @0.20 | (b) total>=3x worst day @0.20 | (c) mean>0 @0.30 | (d) worst day <5% of base @0.20 | USEFUL |", "|---|---|---|---|---|---|"]
    for v in "ABC":
        p = R["pass_rule"][v]
        lines.append(f"| {v} | {p['a']} | {p['b']} | {p['c']} | {p['d']} | **{p['useful']}** |")
    return "\n".join(lines)


if __name__ == "__main__":
    print("## main\n", main_table(), "\n## returns\n", returns_table(), "\n## exit reasons\n", reasons_table(), "\n## DTE @0.20\n", dte_table(),
          "\n## skips\n", skips_table(), "\n## pass\n", pass_table(), f"\n capital={R['capital']} widest={R['widest_wing_structure_pts']} C_on_margin_only={R['C_on_margin_only']}")
