"""Loop tests, part 2: the batch runner (declaration checks, refusal on a changed rule, shrinking alpha, run-once, resume, parity with Task 5)
and the daily forward job (hand-computed rows, idempotency, catch-up equals day-by-day, open trades wait, dry-run, after-close guard).
Run:  python research/ideas/loop/tests/test_loop_batch_forward.py   (also collected by pytest)."""

import json
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loop_testkit import GAP, NOISE, STRONG, approx, make_5min, make_daily, register_batch, tmp_paths, write_md  # noqa: E402
import batch_runner as br  # noqa: E402
import daily_forward as dfw  # noqa: E402
import loop_stats as ls  # noqa: E402
import registry as reg  # noqa: E402
import rule_engine as rules  # noqa: E402
import trial_ledger as tl  # noqa: E402
import forced_trader_ideas as fi  # noqa: E402

DEV_END_RUN = date(2026, 10, 25)


def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc as e:
        return str(e)
    raise AssertionError(f"expected {exc.__name__}")


# ------------------------------------------------------------------ statistics parity with Task 5
def test_verdict_with_alpha_equals_task5_at_its_own_alpha():
    rng = np.random.default_rng(0)
    for _ in range(300):
        r = dict(n_trades=int(rng.integers(0, 120)), mean_net=float(rng.normal(0, 0.001)), boot_p=float(rng.choice([0.0001, 0.004, 0.005, 0.006, 0.3])),
                 null_p=float(rng.choice([0.0001, 0.004, 0.005, 0.006, 0.3])), first_n=int(rng.integers(0, 3)), second_n=int(rng.integers(0, 3)),
                 first_mean=float(rng.normal(0, 0.001)), second_mean=float(rng.normal(0, 0.001)))
        assert ls.verdict_with_alpha(r, fi.ALPHA) == fi.verdict(r)
    base = dict(n_trades=100, mean_net=0.001, boot_p=0.003, null_p=0.003, first_n=50, second_n=50, first_mean=0.001, second_mean=0.002)
    assert ls.verdict_with_alpha(base, 0.005)[0] == "SURVIVES"
    assert ls.verdict_with_alpha(base, 0.0025)[0] == "REJECT"  # the same numbers fail once the batch alpha has shrunk
    assert ls.verdict_with_alpha(dict(base, boot_p=0.001, null_p=0.001), 0.0025)[0] == "SURVIVES"


def test_evaluate_equals_task5_evaluate_idea_at_batch1_settings():
    d, _ = make_daily(700, seed=11)
    t = fi.idea4_forced_sellers(d, drop=0.0)  # lots of trades, any down day
    a, b = fi.evaluate_idea(t), ls.evaluate(t, fi.COST, fi.ALPHA)
    for k in ("n_trades", "mean_net", "mean_gross", "boot_p", "null_p", "first_mean", "second_mean", "verdict"):
        assert a[k] == b[k], k
    c = ls.evaluate(t, 0.0005, 0.01)  # cost and alpha really are parameters
    assert c["mean_net"] > a["mean_net"] and c["alpha"] == 0.01


# ------------------------------------------------------------------ batch runner
def setup_batch(batch=2, ideas=None, seed=1):
    p, td = tmp_paths()
    ideas = ideas or {"strong": STRONG, "noise": NOISE, "gap": GAP}
    md = register_batch(p, batch, ideas, DEV_END_RUN)
    d, v = make_daily(1200, seed=seed)
    return p, td, md, (d, v, None)


def test_batch_runs_each_idea_once_with_shrinking_alpha_and_promotes_only_survivors():
    p, td, md, data = setup_batch()
    with td:
        out = br.run_batch(2, md, p, DEV_END_RUN, data)
        assert len(out) == 3
        bs = tl.events("batch_start", p)
        assert len(bs) == 1 and bs[0]["prior_trials"] == 10 and bs[0]["n_ideas"] == 3
        approx(bs[0]["alpha"], 0.05 / 13)  # Batch 1 counts as 10, plus the 3 new ideas
        assert tl.total_trials(p) == 13
        assert all(e["alpha"] == bs[0]["alpha"] for e in tl.events("trial", p)[10:])
        assert reg.get("B2-01", p)["status"] == "forward" and reg.get("B2-01", p)["verdict"] == "SURVIVES"
        assert reg.get("B2-01", p)["forward_since"] == str(DEV_END_RUN)
        assert reg.get("B2-01", p)["dev_max_drawdown"] >= 0
        assert reg.get("B2-02", p)["status"] == "rejected" and reg.get("B2-03", p)["status"] == "rejected"
        assert reg.problems(p) == []
        assert (p.results / "batch2_results.md").exists() and (p.results / "batch2_results.json").exists()
        # run-once: a second call does nothing and adds no trial
        assert br.run_batch(2, md, p, DEV_END_RUN, data) == []
        assert tl.total_trials(p) == 13 and len(tl.events("batch_start", p)) == 1
        # the next batch is harder: 13 trials so far + 2 new = 15
        md3 = register_batch(p, 3, {"s2": dict(NOISE, conditions=[{"feature": "weekday", "op": "==", "value": 4}]), "s3": dict(GAP, conditions=[{"feature": "gap_next", "op": "abs_gt", "value": 0.02}])}, DEV_END_RUN)
        br.run_batch(3, md3, p, DEV_END_RUN, data)
        approx(tl.events("batch_start", p)[1]["alpha"], 0.05 / 15)
        assert tl.events("batch_start", p)[1]["alpha"] < bs[0]["alpha"]
        assert tl.total_trials(p) == 15


def test_batch_matches_task5_numbers_for_the_same_trades():
    p, td, md, data = setup_batch(ideas={"strong": STRONG})
    with td:
        res = br.run_batch(2, md, p, DEV_END_RUN, data)[0]
        t = rules.to_trades(1, "x", rules.scan(STRONG, data[0]))
        ref = fi.evaluate_idea(t)  # Task 5's own function on the same trades (its alpha/cost are the batch 1 values, same cost here)
        for k in ("n_trades", "mean_net", "boot_p", "null_p", "first_mean", "second_mean"):
            assert res[k] == ref[k], k


def test_refuses_to_run_when_the_rule_changed_after_registration():
    p, td, md, data = setup_batch()
    with td:
        rows = reg.load(p)
        before = len(tl.read(p))
        r = next(x for x in rows if x["id"] == "B2-01")
        r["rule"]["conditions"][0]["value"] = 0.5  # edit the rule, keep the stored hash
        reg._save(rows, p)
        msg = raises(br.BatchRefused, br.run_batch, 2, md, p, DEV_END_RUN, data)
        assert "rule" in msg
        assert len(tl.read(p)) == before and tl.total_trials(p) == 10  # nothing was run, nothing was logged
        r["rule_hash"] = rules.rule_hash(r["rule"])  # edit the hash too: the ledger copy catches it
        reg._save(rows, p)
        raises(br.BatchRefused, br.run_batch, 2, md, p, DEV_END_RUN, data)
        assert len(tl.read(p)) == before
        # a rule that is no longer valid at all is refused too
        r["rule"]["entry"] = {"day": 0, "px": "open"}
        reg._save(rows, p)
        raises(br.BatchRefused, br.run_batch, 2, md, p, DEV_END_RUN, data)
        assert len(tl.read(p)) == before


def test_refuses_without_a_proper_declaration_file():
    p, td, md, data = setup_batch()
    with td:
        before = len(tl.read(p))
        d = md.parent
        raises(br.BatchRefused, br.run_batch, 2, d / "IDEAS_BATCH2_2026-10-25_missing.md", p, DEV_END_RUN, data)
        wrong = d / "notes.md"
        shutil.copy(md, wrong)
        raises(br.BatchRefused, br.run_batch, 2, wrong, p, DEV_END_RUN, data)
        other = d / "IDEAS_BATCH7_2026-10-25.md"
        shutil.copy(md, other)
        raises(br.BatchRefused, br.run_batch, 2, other, p, DEV_END_RUN, data)  # file is for another batch number
        future = write_md(p, 2, date(2027, 1, 1))
        raises(br.BatchRefused, br.run_batch, 2, future, p, DEV_END_RUN, data)  # dated after the run day
        short = d / "IDEAS_BATCH2_2026-10-26.md"
        short.write_text("# Batch 2\n" + "\n".join(f"| {r['id']} | no hash here |" for r in reg.batch_of(2, p)))
        raises(br.BatchRefused, br.run_batch, 2, short, p, date(2026, 10, 26), data)  # names the ideas but not their rule hashes
        assert len(tl.read(p)) == before
        raises(br.BatchRefused, br.run_batch, 9, md, p, DEV_END_RUN, data)  # no such batch


def test_cannot_run_batch1_or_an_idea_that_is_not_proposed():
    p, td, md, data = setup_batch()
    with td:
        raises(br.BatchRefused, br.run_batch, 1, md, p, DEV_END_RUN, data)  # batch 1 ideas have no runnable rule and are not proposed
        reg.set_status("B2-02", "tested", "tampered", p)
        raises(br.BatchRefused, br.run_batch, 2, md, p, DEV_END_RUN, data)


def test_crash_midway_then_resume_keeps_alpha_and_counts_each_trial_once():
    p, td, md, data = setup_batch()
    with td:
        real = rules.scan
        calls = {"n": 0}

        def flaky(*a, **k):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("boom")
            return real(*a, **k)
        rules.scan = flaky
        try:
            raises(RuntimeError, br.run_batch, 2, md, p, DEV_END_RUN, data)
        finally:
            rules.scan = real
        assert tl.total_trials(p) == 11  # only the first idea finished
        alpha = tl.events("batch_start", p)[0]["alpha"]
        br.run_batch(2, md, p, DEV_END_RUN, data)
        assert tl.total_trials(p) == 13 and len(tl.events("batch_start", p)) == 1
        assert tl.events("batch_start", p)[0]["alpha"] == alpha
        assert sorted(e["idea_id"] for e in tl.events("trial", p)[10:]) == ["B2-01", "B2-02", "B2-03"]


def test_dev_data_loader_refuses_holdout_paths_and_missing_files():
    raises(br.BatchRefused, br.load_dev_data, Path("/home/x/.nifty_Holdout/dev"), {"daily": True})
    p, td = tmp_paths()
    with td:
        raises(br.BatchRefused, br.load_dev_data, p.dev_dir, {"daily": True})


# ------------------------------------------------------------------ daily forward job
def forward_setup(rule=STRONG, since_row=1000, n=1300, seed=21):
    d, v = make_daily(n, seed=seed)
    idea = {"id": "B2-01", "batch": 2, "cost": 0.001, "rule": rule, "forward_since": str(d["date"].iloc[since_row].date())}
    return d, idea, since_row


def test_forward_rows_hand_computed_and_cost_applied():
    d, idea, k = forward_setup()
    with_dir = Path(__import__("tempfile").mkdtemp())
    log = with_dir / "log.csv"
    asof = d["date"].iloc[k + 100].date()
    s = dfw.run_day(asof, [idea], (d, None, None), log)
    L = dfw.read_log(log)
    # signals k+1 .. k+99 (their next-day exit is <= row k+100); the signal on row k itself is not after forward_since
    assert len(L) == 99 == s["new_rows"]
    assert L["signal_date"].min() == d["date"].iloc[k + 1] and L["signal_date"].max() == d["date"].iloc[k + 99]
    i = k + 40
    prev_ret = d["close"].iloc[i] / d["close"].iloc[i - 1] - 1
    row = L[L["signal_date"] == d["date"].iloc[i]].iloc[0]
    g = d["close"].iloc[i + 1] / d["open"].iloc[i + 1] - 1
    assert bool(row["triggered"]) == (prev_ret <= 1e-12)
    approx(row["gross_long"], g, 1e-12)
    approx(row["net"], (g - 0.001) if row["triggered"] else 0.0, 1e-12)
    assert (L.loc[~L["triggered"], "net"] == 0).all() and (L.loc[L["triggered"], "cost"] == 0.001).all()
    assert (L["exit_date"] <= pd.Timestamp(asof)).all() and (L["signal_date"] > pd.Timestamp(idea["forward_since"])).all()
    assert dfw.check_log(log) == []


def test_forward_is_idempotent_and_catch_up_equals_day_by_day():
    d, idea, k = forward_setup()
    tmp = Path(__import__("tempfile").mkdtemp())
    a, b = tmp / "a.csv", tmp / "b.csv"
    asof = d["date"].iloc[k + 50].date()
    dfw.run_day(asof, [idea], (d, None, None), a)
    first = a.read_bytes()
    r = dfw.run_day(asof, [idea], (d, None, None), a)  # same day again: nothing new
    assert r["new_rows"] == 0 and a.read_bytes() == first
    for _ in range(3):
        dfw.run_day(asof, [idea], (d, None, None), a)
    assert a.read_bytes() == first
    nxt = d["date"].iloc[k + 51].date()
    r = dfw.run_day(nxt, [idea], (d, None, None), a)
    assert r["new_rows"] == 1  # exactly the one start day that finished today
    # a job that ran every day gives the same file as one catch-up run
    for j in range(2, 51):
        dfw.run_day(d["date"].iloc[k + j].date(), [idea], (d, None, None), b)
    dfw.run_day(nxt, [idea], (d, None, None), b)
    pd.testing.assert_frame_equal(dfw.read_log(a).drop(columns="logged_on"), dfw.read_log(b).drop(columns="logged_on"))  # only the bookkeeping date differs
    assert dfw.check_log(a) == []


def test_open_trades_wait_until_they_finish_and_dev_days_never_enter():
    hold3 = {"kind": "daily", "conditions": [{"feature": "ret_1d", "op": "<=", "value": 0.0}], "direction": {"fixed": 1},
             "entry": {"day": 0, "px": "close"}, "exit": {"day": 3, "px": "close"}}
    d, idea, k = forward_setup(hold3)
    tmp = Path(__import__("tempfile").mkdtemp())
    log = tmp / "l.csv"
    dfw.run_day(d["date"].iloc[k + 10].date(), [idea], (d, None, None), log)
    L = dfw.read_log(log)
    assert L["signal_date"].max() == d["date"].iloc[k + 7]  # signal k+8 would exit on k+11: still open
    assert len(L) == 7
    dfw.run_day(d["date"].iloc[k + 11].date(), [idea], (d, None, None), log)
    assert dfw.read_log(log)["signal_date"].max() == d["date"].iloc[k + 8]
    # a very early asof (inside the dev period) records nothing, whatever the data holds
    log2 = tmp / "l2.csv"
    r = dfw.run_day(d["date"].iloc[k - 200].date(), [idea], (d, None, None), log2)
    assert r["new_rows"] == 0 and not log2.exists()


def test_forward_signal_uses_only_data_known_that_day():
    d, idea, k = forward_setup()
    tmp = Path(__import__("tempfile").mkdtemp())
    live, full = tmp / "live.csv", tmp / "full.csv"
    stop = k + 60
    dfw.run_day(d["date"].iloc[stop].date(), [idea], (d.iloc[: stop + 1], None, None), live)  # data stops at asof
    dfw.run_day(d["date"].iloc[stop].date(), [idea], (d, None, None), full)  # the file holds the future too: must not matter
    pd.testing.assert_frame_equal(dfw.read_log(live), dfw.read_log(full))


def test_forward_intraday_and_two_ideas_in_one_run():
    m = make_5min(40)
    ir = {"kind": "intraday", "signal": {"from": "o:1415", "to": "o:1515"}, "conditions": [{"feature": "sig_ret", "op": "!=", "value": 0}],
          "direction": {"with": "sig_ret"}, "entry": "o:1515", "exit": "c:1525"}
    days = sorted(m["date"].dt.normalize().unique())
    i5 = {"id": "B2-02", "batch": 2, "cost": 0.001, "rule": ir, "forward_since": str(pd.Timestamp(days[9]).date())}
    d, i1, k = forward_setup()
    tmp = Path(__import__("tempfile").mkdtemp())
    log = tmp / "l.csv"
    asof = pd.Timestamp(days[29]).date()
    dfw.run_day(asof, [i5], (None, None, m), log)
    L = dfw.read_log(log)
    assert len(L) == 20 and set(L["idea_id"]) == {"B2-02"} and (L["entry_date"] == L["exit_date"]).all()
    day = pd.Timestamp(days[15])
    sub = m[m["date"].dt.normalize() == day]
    bars = sub.set_index(sub["date"].dt.strftime("%H%M"))
    sig = bars.loc["1515", "open"] / bars.loc["1415", "open"] - 1
    g = bars.loc["1525", "close"] / bars.loc["1515", "open"] - 1
    row = L[L["signal_date"] == day].iloc[0]
    approx(row["gross_long"], g, 1e-12)
    approx(row["net"], np.sign(sig) * g - 0.001, 1e-12)
    dfw.run_day(d["date"].iloc[k + 5].date(), [i1], (d, None, None), log)  # a second idea can share the log
    both = dfw.read_log(log)
    assert set(both["idea_id"]) == {"B2-01", "B2-02"} and not both.duplicated(["idea_id", "signal_date"]).any()
    corrupt = both.copy()
    corrupt = pd.concat([corrupt, corrupt.iloc[:1]])
    corrupt.to_csv(tmp / "bad.csv", index=False)
    assert dfw.check_log(tmp / "bad.csv") == ["duplicate (idea, signal day) rows"]


def test_dry_run_reads_dev_csvs_cut_at_the_simulated_today():
    d, v = make_daily(300, vix=True, seed=8)
    tmp = Path(__import__("tempfile").mkdtemp())
    dev = tmp / "dev"
    dev.mkdir()
    d.to_csv(dev / "nifty_day_dev.csv", index=False)
    v.to_csv(dev / "india_vix_day.csv", index=False)
    asof = d["date"].iloc[200].date()
    idea = {"id": "B2-01", "rule": STRONG}
    dd, vv, mm = dfw.dry_data(dev, asof, [idea])
    assert dd["date"].max() == pd.Timestamp(asof) and vv is None and mm is None  # a daily-only rule loads only the daily file
    vix_rule = {"id": "B2-02", "rule": {"kind": "daily", "conditions": [{"feature": "vix_chg_1d", "op": ">=", "value": 0.1}], "direction": {"fixed": 1},
                                        "entry": {"day": 0, "px": "close"}, "exit": {"day": 1, "px": "close"}}}
    dd, vv, mm = dfw.dry_data(dev, asof, [vix_rule])
    assert vv["date"].max() == pd.Timestamp(asof)
    log = tmp / "out" / "forward_log_dryrun.csv"
    idea = dict(idea, batch=2, cost=0.001, forward_since=str(d["date"].iloc[150].date()))
    s1 = dfw.run_day(asof, [idea], dfw.dry_data(dev, asof, [idea]), log)
    s2 = dfw.run_day(asof, [idea], dfw.dry_data(dev, asof, [idea]), log)
    assert s1["new_rows"] == 49 and s2["new_rows"] == 0  # idempotent in dry-run mode too
    raises(SystemExit, dfw.dry_data, Path("/x/.nifty_holdout"), asof, [idea])
    raises(SystemExit, dfw.dry_data, tmp / "nowhere", asof, [idea])


def test_after_close_guard():
    from zoneinfo import ZoneInfo
    ist = ZoneInfo("Asia/Kolkata")
    day = date(2026, 11, 3)
    assert not dfw.after_close_ist(day, datetime(2026, 11, 3, 15, 44, tzinfo=ist))
    assert dfw.after_close_ist(day, datetime(2026, 11, 3, 15, 45, tzinfo=ist))
    assert dfw.after_close_ist(day, datetime(2026, 11, 4, 9, 0, tzinfo=ist))  # an earlier day is always final
    assert not dfw.after_close_ist(date(2026, 11, 5), datetime(2026, 11, 4, 20, 0, tzinfo=ist))  # the future is not


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except Exception as e:  # noqa: BLE001
                import traceback
                fails += 1
                print("FAIL", name, repr(e))
                traceback.print_exc(limit=-3)
    print("all passed" if not fails else f"{fails} FAILED")
    sys.exit(1 if fails else 0)
