"""Run the ONE pre-registered Batch 4 trial (wheel vs buy-and-hold) plus the three listed controls, ONCE.
Rules: research/RESULTS.md ("Planned ... branch claude/employee-wheel"); study text docs/ideas/IDEAS_BATCH4_WHEEL_2026-10-18.md. No argument changes a rule.
Writes research/wheel/results/*. With --record it also appends the batch and the trial to the loop's append-only trial ledger (once; refuses a second time).
  python research/wheel/wheel_run.py [--record]"""

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wheel_core as wc  # noqa: E402

OUT = HERE / "results"
MD = HERE.parent.parent / "docs" / "ideas" / "IDEAS_BATCH4_WHEEL_2026-10-18.md"
SHIFTS = (1, 2)


def rs(x):
    return "n/a" if x != x else f"{x:+,.0f}"


def run() -> dict:
    bars, closes, expiries = wc.load_index()
    cache: dict = {}

    def loader(ex, k, kind):
        key = (ex, k, kind)
        if key not in cache:
            cache[key] = wc.sb.load_leg(ex, k, kind)
        return cache[key]

    plans = {("causal", s): wc.make_plans(bars, expiries, s, "causal") for s in (0,) + SHIFTS}
    plans[("as_written", 0)] = wc.make_plans(bars, expiries, 0, "as_written")
    notional = plans[("causal", 0)][0]["spot"] * wc.LOT
    res = {"expiries": len(expiries), "first_expiry": str(expiries[0]), "last_expiry": str(expiries[-1]), "notional": notional,
           "first_entry_spot": plans[("causal", 0)][0]["spot"], "by_slip": {}, "weeks": {}}
    for slip in wc.SLIPS:
        key = f"{slip:.2f}"
        block = {}
        for mode in wc.MODES:
            rows = wc.run_weeks(plans[("causal", 0)], closes, loader, slip, mode)
            block[mode] = wc.summarise(rows, notional)
            if slip == wc.DECISION_SLIP:
                res["weeks"][mode] = rows
        for s in SHIFTS:
            p = plans[("causal", s)]
            rows = wc.run_weeks(p, closes, loader, slip, "wheel")
            block[f"shift_{s}"] = wc.summarise(rows, p[0]["spot"] * wc.LOT)
        rows = wc.run_weeks(plans[("as_written", 0)], closes, loader, slip, "wheel")
        block["lookahead_as_written"] = wc.summarise(rows, plans[("as_written", 0)][0]["spot"] * wc.LOT)
        res["by_slip"][key] = block
    res["primary"] = res["by_slip"]["0.20"]["wheel"]
    res["controls"] = {k: res["by_slip"]["0.20"][k] for k in ("put_only", "call_only", "shift_1", "shift_2")}
    res["lookahead_diag"] = res["by_slip"]["0.20"]["lookahead_as_written"]
    # window-only extras for the report: sample moves and entry-day counts (descriptive)
    p0 = plans[("causal", 0)]
    res["index_first_entry_to_last_close"] = closes[expiries[-1]] - p0[0]["spot"]
    res["causal_entry_days_moved_vs_selling_rule"] = sum(a["entry_day"] != b["entry_day"] for a, b in zip(p0, plans[("as_written", 0)]))
    return res


def write_weeks(res: dict) -> None:
    OUT.mkdir(exist_ok=True)
    cols = ["k", "expiry", "entry_day", "entry_ts", "spot", "state_start", "kind", "strike", "fill", "skipped", "settle", "event", "state_end", "premium_rs",
            "fees_rs", "intrinsic_rs", "stt_rs", "exposure_mark_rs", "expo_cost_rs", "net_rs", "bench_rs", "d_rs", "cash_info_rs"]
    for mode, rows in res["weeks"].items():
        with (OUT / f"weeks_{mode}_0.20.csv").open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            for r in rows:
                w.writerow([r[c] for c in cols])


def record(res: dict, paths=None) -> None:
    sys.path.insert(0, str(HERE.parent / "ideas" / "loop"))
    import trial_ledger as tl
    if tl.trial_for("B4-01", paths) is not None:
        raise SystemExit("B4-01 is already in the ledger; refusing to append twice")
    prior = tl.total_trials(paths)
    alpha = tl.batch_alpha(prior, 1)
    assert prior == 13 and abs(alpha - wc.ALPHA) < 1e-12, (prior, alpha)
    p = res["primary"]
    if MD.exists():
        text = MD.read_text()
        rules = text[text.index("## Rules"):text.index("## Controls")]
        rule_hash, md_hash = hashlib.sha256(rules.encode()).hexdigest(), hashlib.sha256(MD.read_bytes()).hexdigest()
    else:
        rule_hash = md_hash = "n/a"
    tl.append({"event": "batch_start", "batch": 4, "prior_trials": prior, "n_ideas": 1, "alpha": alpha, "md_file": MD.name, "md_sha256": md_hash,
               "ideas": {"B4-01": rule_hash}, "source": "Task 8 (research/wheel)"}, paths)
    tl.append({"event": "trial", "idea_id": "B4-01", "batch": 4, "rule_hash": rule_hash, "alpha": alpha, "name": "Wheel (index proxy) vs buy-and-hold",
               "source": "research/wheel/results/wheel_results.json", "n_trades": p["n_traded"], "n_weeks": p["n_weeks"], "mean_net": p["D"]["mean"],
               "boot_p": p["boot_p"], "null_p": None, "verdict": p["verdict"], "checks": p["checks"]}, paths)


def line(name, s):
    d = s["D"]
    return (f"  {name:<22} traded {s['n_traded']}/{s['n_weeks']}  wheel total {rs(s['wheel']['total'])} (bench {rs(s['bench']['total'])})  mean D {rs(d['mean'])}  "
            f"boot p {s['boot_p']:.4f}  halves {rs(s['halves']['first_mean'])} / {rs(s['halves']['second_mean'])}  max DD {rs(s['wheel']['max_drawdown'])} vs {rs(s['bench']['max_drawdown'])}  -> {s['verdict']}")


def report(res: dict) -> str:
    p = res["primary"]
    h = p["halves"]
    L = [f"Wheel vs buy-and-hold: {res['expiries']} weeks ({res['first_expiry']} to {res['last_expiry']}), lot 75 (unverified), notional Rs{res['notional']:,.0f} (first entry spot {res['first_entry_spot']:.1f}); alpha {wc.ALPHA:.6f}",
         f"  skipped weeks ({p['n_skipped']}): {p['skipped']}",
         "", "PRIMARY (slippage 0.20)", line("wheel", p),
         f"  halves split {h['midpoint']}: first n={h['first_n']} mean D {rs(h['first_mean'])} | second n={h['second_n']} mean D {rs(h['second_mean'])}; checks {p['checks']}",
         f"  wheel: total {rs(p['wheel']['total'])}  return {p['total_return_wheel']:.2%}  mean {rs(p['wheel']['mean'])}  median {rs(p['wheel']['median'])}  worst wk {rs(p['wheel']['worst_week'])}  best wk {rs(p['wheel']['best_week'])}  max DD {rs(p['wheel']['max_drawdown'])}  sharpe-like {p['wheel']['sharpe_like']:.3f}",
         f"  bench: total {rs(p['bench']['total'])}  return {p['total_return_bench']:.2%}  mean {rs(p['bench']['mean'])}  median {rs(p['bench']['median'])}  worst wk {rs(p['bench']['worst_week'])}  best wk {rs(p['bench']['best_week'])}  max DD {rs(p['bench']['max_drawdown'])}  sharpe-like {p['bench']['sharpe_like']:.3f}",
         f"  D (wheel - bench): total {rs(p['D']['total'])} mean {rs(p['D']['mean'])} median {rs(p['D']['median'])} worst {rs(p['D']['worst_week'])} best {rs(p['D']['best_week'])}",
         f"  time: weeks starting CASH {p['weeks_start_cash']} / LONG {p['weeks_start_long']}; assignments {p['assignments']}; called away {p['called_away']}",
         f"  money: premium collected {rs(p['premium_rs'])}; intrinsic paid {rs(-p['intrinsic_paid_rs'])}; exposure marks {rs(p['exposure_marks_rs'])}; option fees {rs(-p['option_fees_rs'])}; settlement STT {rs(-p['settle_stt_rs'])}; exposure costs {rs(-p['exposure_costs_rs'])}",
         f"  idle-cash information (6.5% on weeks starting CASH): +Rs{p['idle_cash_info_rs']:,.0f} -> wheel total with idle cash {rs(p['wheel_plus_idle_cash_total'])} ({p['wheel_plus_idle_cash_total'] / p['notional']:.2%})",
         f"  index move first entry spot -> last close: {res['index_first_entry_to_last_close']:+,.0f} points; causal entry day differs from the selling-rule day in {res['causal_entry_days_moved_vs_selling_rule']} of {res['expiries']} weeks",
         "", "SLIPPAGE SWEEP (wheel vs benchmark)"]
    for sl, blk in res["by_slip"].items():
        L.append(line(f"slip {sl}", blk["wheel"]))
    L += ["", "CONTROLS at 0.20 (not trials; D is vs the same benchmark)"]
    names = {"put_only": "1 short-put-only", "call_only": "2 covered-call-only", "shift_1": "3a wheel entry +1 bar", "shift_2": "3b wheel entry +2 bars"}
    for k, nm in names.items():
        s = res["controls"][k]
        L.append(line(nm, s) + f"  [assign {s['assignments']}, called {s['called_away']}, skipped {s['n_skipped']}]")
    po, w = res["controls"]["put_only"], p
    L.append(f"  does the call overlay help? wheel total {rs(w['wheel']['total'])} vs put-only {rs(po['wheel']['total'])}: difference {rs(w['wheel']['total'] - po['wheel']['total'])}; max DD {rs(w['wheel']['max_drawdown'])} vs {rs(po['wheel']['max_drawdown'])}")
    L += ["", "LOOKAHEAD DIAGNOSTIC (as-written selling-rule entry day = before the previous settlement; NOT tradeable, NOT used for the verdict)"]
    L.append(line("as-written timing", res["lookahead_diag"]))
    L += ["", "controls and diagnostic at other slippages (mean D): " + "; ".join(
        f"{sl}: " + ", ".join(f"{k} {rs(b[k]['D']['mean'])}" for k in ("put_only", "call_only", "shift_1", "shift_2", "lookahead_as_written")) for sl, b in res["by_slip"].items())]
    return "\n".join(L)


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--record", action="store_true", help="append the batch and the trial to the loop ledger")
    a = a.parse_args()
    res = run()
    write_weeks(res)
    slim = {k: v for k, v in res.items() if k != "weeks"}
    (OUT / "wheel_results.json").write_text(json.dumps(slim, indent=1, default=str))
    txt = report(res)
    (OUT / "wheel_results.txt").write_text(txt + "\n")
    print(txt)
    if a.record:
        record(res)
        print("\nledger: recorded batch 4 (B4-01)")
