"""Loop tests, part 3: promotion and retirement edge cases, the paper-book filters (hand-computed), an end-to-end run
(batch -> forward days -> promotion), the weekly report, and hygiene (no holdout, no order code, no secrets, no scheduling).
Run:  python research/ideas/loop/tests/test_loop_promotion_report.py   (also collected by pytest)."""

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loop_testkit import LOOP, NOISE, STRONG, approx, make_daily, register_batch, tmp_paths  # noqa: E402
import batch_runner as br  # noqa: E402
import daily_forward as dfw  # noqa: E402
import loop_config as cfg  # noqa: E402
import loop_stats as ls  # noqa: E402
import promotion as pr  # noqa: E402
import registry as reg  # noqa: E402
import trial_ledger as tl  # noqa: E402
import weekly_report as wr  # noqa: E402


def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc as e:
        return str(e)
    raise AssertionError(f"expected {exc.__name__}")


GOOD = dict(days=60, trades=20, mean_net=0.001, boot_p=0.01, null_p=0.01)


# ------------------------------------------------------------------ promotion edge cases
def test_promotion_thresholds_are_exact():
    assert all(pr.promotion_checks(GOOD).values())
    assert not pr.promotion_checks(dict(GOOD, days=59))["days>=60"]  # 59 days is not enough, 60 is
    assert not pr.promotion_checks(dict(GOOD, trades=19))["trades>=20"]
    assert not pr.promotion_checks(dict(GOOD, mean_net=0.0))["net_mean>0"]  # exactly zero is not "> 0"
    assert not pr.promotion_checks(dict(GOOD, mean_net=-1e-9))["net_mean>0"]
    assert not pr.promotion_checks(dict(GOOD, trades=0, mean_net=float("nan")))["net_mean>0"]
    assert not pr.promotion_checks(dict(GOOD, boot_p=0.05))["boot_p<0.05"]  # strictly below
    assert pr.promotion_checks(dict(GOOD, boot_p=0.0499))["boot_p<0.05"]
    assert not pr.promotion_checks(dict(GOOD, null_p=0.05))["null_p<0.05"]  # must also beat random entries
    assert not all(pr.promotion_checks(dict(GOOD, null_p=0.4)).values())


def test_retire_rules_are_exact():
    def st(net, days=40, dd=0.0):
        return dict(last_window_net=net, last_window_days=days, drawdown=dd)
    assert pr.retire_checks(st(-1e-9), 0.1) == {"retire_rolling40": True, "retire_drawdown": False}
    assert pr.retire_checks(st(0.0), 0.1)["retire_rolling40"] is False  # a 40-day mean of exactly 0 is not "< 0"
    assert pr.retire_checks(st(-0.5, days=39), 0.1)["retire_rolling40"] is False  # fewer than 40 days: the rule cannot fire
    assert pr.retire_checks(st(0.01, dd=0.2), 0.1)["retire_drawdown"] is False  # exactly 2 x dev drawdown: not more than
    assert pr.retire_checks(st(0.01, dd=0.2000001), 0.1)["retire_drawdown"] is True
    assert pr.retire_checks(st(0.01, dd=9.0), None)["retire_drawdown"] is False  # no dev drawdown on file: cannot judge
    assert pr.retire_checks(st(0.01, dd=0.0), 0.0)["retire_drawdown"] is False
    assert pr.retire_checks(st(0.01, dd=1e-9), 0.0)["retire_drawdown"] is True


def test_max_drawdown_hand_computed():
    # running sum 0, .01, -.01, -.005, -.015, .015 -> peaks 0,.01,.01,.01,.01,.015 -> falls 0,0,.02,.015,.025,0
    approx(ls.max_drawdown([0.01, -0.02, 0.005, -0.01, 0.03]), 0.025, 1e-15)
    assert ls.max_drawdown([]) == 0.0 and ls.max_drawdown([0.01, 0.02]) == 0.0
    approx(ls.max_drawdown([-0.03, 0.01]), 0.03, 1e-15)  # the start counts as a peak of zero


def fake_rows(idea_id, nets, start="2026-11-02", trig=None):
    dts = pd.bdate_range(start, periods=len(nets))
    trig = [True] * len(nets) if trig is None else trig
    nets = np.asarray(nets, float)
    return pd.DataFrame({"idea_id": idea_id, "signal_date": dts, "entry_date": dts, "exit_date": dts, "triggered": trig, "direction": np.where(trig, 1.0, 0.0),
                         "gross_long": nets + 0.001, "cost": 0.001, "net": np.where(trig, nets, 0.0), "batch": 2, "logged_on": "x"})


def test_forward_stats_hand_computed():
    rows = fake_rows("B2-01", [0.01, -0.01, 0.02, 0.0, 0.03], trig=[True, True, True, False, True])
    s = pr.forward_stats(rows, 0.001, with_null=False)
    assert s["days"] == 5 and s["trades"] == 4
    approx(s["mean_net"], (0.01 - 0.01 + 0.02 + 0.03) / 4, 1e-15)
    approx(s["total_net"], 0.05, 1e-15)
    approx(s["drawdown"], 0.01, 1e-15)  # the one -1% after a +1% peak
    approx(s["last_window_net"], 0.05, 1e-15) and s["last_window_days"] == 5


# ------------------------------------------------------------------ the paper book (filters)
def trades(*rows):
    return pd.DataFrame([{"idea_id": i, "signal_date": pd.Timestamp(s), "entry_date": pd.Timestamp(e), "exit_date": pd.Timestamp(x), "net": n} for i, s, e, x, n in rows])


def book(rows, **kw):
    cal = set(rows["signal_date"]) | set(rows["exit_date"])
    return pr.build_book(rows, cal, **kw)


def test_book_size_cap_and_pnl_hand_computed():
    b = book(trades(("A", "2026-11-02", "2026-11-02", "2026-11-03", 0.01)), ideas={"A": 3})
    assert b["lots"].iloc[0] == 1 and b["status"].iloc[0] == "taken"  # asked for 3 lots, capped at 1
    approx(b["pnl_rs"].iloc[0], 0.01 * 1 * cfg.LOT_NOTIONAL_RS, 1e-9)  # 0.01 x 1,500,000 = Rs 15,000
    approx(pr.build_book(trades(("A", "2026-11-02", "2026-11-02", "2026-11-03", -0.004)), ["2026-11-02"], lot_rs=1000)["pnl_rs"].iloc[0], -4.0, 1e-12)


def test_book_one_position_per_idea():
    b = book(trades(("A", "2026-11-02", "2026-11-02", "2026-11-06", 0.01),  # held Mon..Thu
                    ("A", "2026-11-03", "2026-11-03", "2026-11-04", 0.01),  # starts inside it: skipped
                    ("A", "2026-11-06", "2026-11-06", "2026-11-09", 0.01)))  # starts the day the first exits: allowed (exit day is free)
    assert list(b["status"]) == ["taken", "skipped_overlap", "taken"]
    assert b["pnl_rs"].sum() == 2 * 0.01 * cfg.LOT_NOTIONAL_RS


def test_book_portfolio_cap_counts_same_day_trades_too():
    rows = trades(("A", "2026-11-02", "2026-11-02", "2026-11-06", 0.01), ("B", "2026-11-02", "2026-11-02", "2026-11-05", 0.01),
                  ("C", "2026-11-03", "2026-11-03", "2026-11-04", 0.01), ("D", "2026-11-05", "2026-11-05", "2026-11-05", 0.01))
    b = book(rows, cap=2)
    assert list(b["status"]) == ["taken", "taken", "skipped_portfolio_cap", "taken"]  # D is a same-day trade after B has exited
    b3 = book(rows, cap=3)
    assert list(b3["status"]) == ["taken", "taken", "taken", "taken"]
    same = trades(("A", "2026-11-02", "2026-11-02", "2026-11-02", 0.01), ("B", "2026-11-02", "2026-11-02", "2026-11-02", 0.01))
    assert list(book(same, cap=1)["status"]) == ["taken", "skipped_portfolio_cap"]  # two intraday trades on one day overlap


def test_book_daily_loss_limit_pauses_the_next_day_only():
    bad = ("A", "2026-11-02", "2026-11-02", "2026-11-03", -0.0100001)  # exits Tue 3rd with Rs -15,000.15: just over the limit
    rows = trades(bad, ("B", "2026-11-03", "2026-11-04", "2026-11-04", 0.01), ("B", "2026-11-04", "2026-11-05", "2026-11-05", 0.01))
    b = book(rows, loss_limit=15_000)
    # B's first trade enters Wed 4th, the day after the losing day (Tue 3rd): paused; the trade on Thu 5th is fine
    assert list(b["status"]) == ["taken", "skipped_loss_pause", "taken"]
    exact = trades(("A", "2026-11-02", "2026-11-02", "2026-11-03", -0.01), ("B", "2026-11-03", "2026-11-04", "2026-11-04", 0.01))
    assert list(book(exact, loss_limit=15_000)["status"]) == ["taken", "taken"]  # a loss of exactly the limit does not pause
    approx(book(rows, loss_limit=15_000)["pnl_rs"].sum(), -0.0100001 * 1.5e6 + 0.01 * 1.5e6, 1e-6)  # skipped trades earn and lose nothing


# ------------------------------------------------------------------ end to end
def end_to_end(forward_rule_data="strong", days_after=110):
    """Batch run on synthetic dev data -> forward days on a longer series -> returns (paths, tmpdir, daily_long, run_date)."""
    p, td = tmp_paths()
    dev, _ = make_daily(1200, seed=1)
    long_, _ = make_daily(1200 + 200, seed=1)  # same seed: the first 1200 rows are identical, then 200 fresh days with the same behaviour
    if forward_rule_data == "noedge":
        long_ = pd.concat([dev, make_daily(200, start=str((dev["date"].iloc[-1] + pd.Timedelta(days=1)).date()), edge=0.0, seed=77)[0]], ignore_index=True)
    run_date = dev["date"].iloc[-1].date()
    md = register_batch(p, 2, {"strong": STRONG}, run_date)
    out = br.run_batch(2, md, p, run_date, (dev, None, None))
    assert out[0]["verdict"] == "SURVIVES"
    return p, td, long_, run_date


def test_end_to_end_survivor_runs_forward_then_is_promoted_once():
    p, td, long_, run_date = end_to_end()
    with td:
        idea = reg.get("B2-01", p)
        assert idea["status"] == "forward" and idea["forward_since"] == str(run_date)
        early = long_["date"].iloc[1199 + 30].date()
        dfw.run_day(early, [idea], (long_, None, None), p.forward_log)
        out = pr.run(early, apply=True, paths=p)
        assert out["decisions"][0]["action"] == "none" and "days>=60" in out["decisions"][0]["reason"]  # 29 days: too soon
        assert reg.get("B2-01", p)["status"] == "forward"
        asof = long_["date"].iloc[1199 + 110].date()
        dfw.run_day(asof, [idea], (long_, None, None), p.forward_log)
        preview = pr.run(asof, apply=False, paths=p)
        assert preview["decisions"][0]["action"] == "promote" and reg.get("B2-01", p)["status"] == "forward"  # preview writes nothing
        s = preview["decisions"][0]["stats"]
        assert s["days"] >= 60 and s["trades"] >= 20 and s["mean_net"] > 0 and s["boot_p"] < 0.05 and s["null_p"] < 0.05
        pr.run(asof, apply=True, paths=p)
        r = reg.get("B2-01", p)
        assert r["status"] == "promoted" and r["promoted_on"] == str(asof)
        assert [e["to"] for e in tl.events("status", p)][-1] == "promoted" and reg.problems(p) == []
        n = len(tl.read(p))
        again = pr.run(asof, apply=True, paths=p)  # idempotent: nothing left to do
        assert len(tl.read(p)) == n and again["decisions"][0]["action"] == "none"
        # trades after promotion go into the paper book, filters applied
        later = long_["date"].iloc[1199 + 160].date()
        dfw.run_day(later, [r], (long_, None, None), p.forward_log)
        out = pr.run(later, apply=True, paths=p)
        bk = pd.read_csv(p.results / "paper_book.csv")
        assert len(bk) > 0 and (bk["status"] == "taken").all() and (pd.to_datetime(bk["signal_date"]) > pd.Timestamp(asof)).all()
        approx(bk["pnl_rs"].sum(), (bk["net"] * cfg.LOT_NOTIONAL_RS).sum(), 1e-6)
        assert pd.to_datetime(bk["exit_date"]).max() <= pd.Timestamp(later)


def test_end_to_end_no_edge_on_fresh_days_is_not_promoted():
    p, td, long_, run_date = end_to_end("noedge")
    with td:
        idea = reg.get("B2-01", p)
        asof = long_["date"].iloc[1199 + 150].date()
        dfw.run_day(asof, [idea], (long_, None, None), p.forward_log)
        d = pr.run(asof, apply=True, paths=p)["decisions"][0]
        assert d["stats"]["days"] >= 60 and d["action"] == "none"  # edge was real in dev, absent forward: stays forward, never promoted
        assert reg.get("B2-01", p)["status"] == "forward"


def promoted_idea(p, dev_dd, since="2026-10-30", promoted="2026-11-01"):
    reg.register("B2-01", 2, "x", "s", STRONG, paths=p)
    reg.set_status("B2-01", "tested", "t", p, dev_max_drawdown=dev_dd)
    reg.set_status("B2-01", "forward", "f", p, forward_since=since)
    reg.set_status("B2-01", "promoted", "p", p, promoted_on=promoted)


def test_retirement_end_to_end_both_rules():
    p, td = tmp_paths()
    with td:
        promoted_idea(p, dev_dd=0.5)
        nets = [0.004] * 30 + [-0.0015] * 40  # +12% then a slow bleed: last 40 days sum -6%, drawdown 6% (limit 2 x 50% = 100%)
        fake = fake_rows("B2-01", nets, start="2026-11-02")
        fake.to_csv(p.forward_log, index=False)
        asof = fake["exit_date"].iloc[-1].date()
        d = pr.decide(reg.get("B2-01", p), dfw.read_log(p.forward_log), asof)
        assert d["action"] == "retire" and d["checks"] == {"retire_rolling40": True, "retire_drawdown": False}
        pr.run(asof, apply=True, paths=p)
        r = reg.get("B2-01", p)
        assert r["status"] == "retired" and r["retired_on"] == str(asof) and "last 40 days" in r["retire_reason"]
        assert pr.run(asof, apply=True, paths=p)["decisions"] == []  # a retired idea is final
    p, td = tmp_paths()
    with td:
        promoted_idea(p, dev_dd=0.01)
        fake = fake_rows("B2-01", [0.004] * 50 + [-0.03] + [0.004] * 20)  # healthy, one -3% day: 3% drawdown > 2 x 1%
        fake.to_csv(p.forward_log, index=False)
        d = pr.decide(reg.get("B2-01", p), dfw.read_log(p.forward_log), fake["exit_date"].iloc[-1].date())
        assert d["checks"] == {"retire_rolling40": False, "retire_drawdown": True} and d["action"] == "retire"
    p, td = tmp_paths()
    with td:
        promoted_idea(p, dev_dd=0.5)
        fake = fake_rows("B2-01", [0.004] * 50 + [-0.03] + [0.004] * 20)
        d = pr.decide(reg.get("B2-01", p), fake, fake["exit_date"].iloc[-1].date())
        assert d["action"] == "none"  # within limits stays promoted


def test_run_refuses_a_damaged_log_or_registry():
    p, td = tmp_paths()
    with td:
        promoted_idea(p, dev_dd=0.5)
        f = fake_rows("B2-01", [0.01] * 3)
        pd.concat([f, f.iloc[:1]]).to_csv(p.forward_log, index=False)
        raises(SystemExit, pr.run, date(2026, 11, 20), True, p)
        f.to_csv(p.forward_log, index=False)
        rows = reg.load(p)
        rows[-1]["status"] = "retired"
        reg._save(rows, p)
        raises(SystemExit, pr.run, date(2026, 11, 20), True, p)


# ------------------------------------------------------------------ weekly report
def test_weekly_report_answers_first_and_counts_correctly():
    p, td, long_, run_date = end_to_end()
    with td:
        asof = long_["date"].iloc[1199 + 110].date()
        dfw.run_day(asof, [reg.get("B2-01", p)], (long_, None, None), p.forward_log)
        before = (p.ledger.read_bytes(), p.registry.read_bytes(), p.forward_log.read_bytes())
        text = wr.build(run_date, p)
        lines = text.splitlines()
        assert lines[0].startswith("# Idea factory: weekly note") and lines[2].startswith("**Answer:")  # answer before any table
        assert "1 new idea tested once each (11 trials counted in total" in text and "Survivors: B2-01." in text
        assert "1 idea running" in text and "None promoted this week." in text and "Retired this week:** none" in text
        assert "p < 0.00238" in text  # 0.05 / (11 + 10)
        assert text.index("**Answer:") < text.index("| Status | Ideas |")
        later = wr.build(asof, p)
        assert "0 new ideas tested" in later and "Forward days" in later
        assert before == (p.ledger.read_bytes(), p.registry.read_bytes(), p.forward_log.read_bytes())  # building a report changes nothing
        pr.run(asof, apply=True, paths=p)
        promo = wr.build(asof, p)
        assert "Promoted this week: B2-01." in promo and "Something moved this week" in promo
        assert wr.build(date(2026, 10, 19), tmp_paths()[0]).splitlines()[2].startswith("**Answer: No new edge")


# ------------------------------------------------------------------ hygiene
LOOP_SOURCES = [f for f in LOOP.glob("*.py")]


def test_no_holdout_no_order_code_no_secrets_in_the_loop_code():
    assert len(LOOP_SOURCES) >= 9
    banned = [".nifty_holdout", "holdout_dir", "kite_data", "expanduser", "place_order", "placeorder", "modify_order", "/v2/order", "/v3/order", "order/place",
              "upstox_analytics_token", "kite_api_key", "kite_access_token", "api_key", "access_token", "bearer ", "authorization", "os.environ", "getenv"]
    for f in LOOP_SOURCES:
        src = f.read_text().lower()
        for bad in banned:
            assert bad not in src, (f.name, bad)


def test_nothing_schedules_itself():
    for f in LOOP_SOURCES:
        src = f.read_text().lower()
        for bad in ("crontab", "croncreate", "schedule.every", "apscheduler", "systemd", "create_trigger", "send_later", "while true"):
            assert bad not in src, (f.name, bad)
    assert not list(LOOP.glob("*.sh")) and not list(LOOP.glob("*.yml")) and not list(LOOP.glob("*.cron"))
    assert not list((LOOP.parents[2] / ".github").glob("**/*loop*")) if (LOOP.parents[2] / ".github").exists() else True


def test_frozen_task5_files_are_untouched_in_the_repo_copy():
    # sha256 of the Task 5 runner as committed when this loop was built (forced_trader_ideas.py code_hash 03e3c77355e8 in the ledger)
    assert (LOOP.parent / "forced_trader_ideas.py").exists() and fi_hash() == "03e3c77355e8"


def fi_hash():
    import forced_trader_ideas as fi
    return fi.code_hash()


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
