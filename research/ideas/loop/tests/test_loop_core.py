"""Loop tests, part 1: ledger (hash chain, trial counter, shrinking alpha), registry (seed, statuses, duplicates, variants, tampering),
rule engine (hand-computed answers, validation, no lookahead, equals the Task 5 functions on the same data).
Run:  python research/ideas/loop/tests/test_loop_core.py   (also collected by pytest)."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loop_testkit import GAP, NOISE, STRONG, approx, make_5min, make_daily, tmp_paths  # noqa: E402
import loop_config as cfg  # noqa: E402,F401
import registry as reg  # noqa: E402
import rule_engine as rules  # noqa: E402
import trial_ledger as tl  # noqa: E402
import forced_trader_ideas as fi  # noqa: E402


def raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc as e:
        return str(e)
    raise AssertionError(f"expected {exc.__name__}")


# ------------------------------------------------------------------ alpha and the global counter
def test_alpha_shrinks_with_every_trial_hand_computed():
    approx(tl.batch_alpha(0, 10), 0.005)  # Batch 1: 0.05 / 10
    approx(tl.batch_alpha(10, 10), 0.0025)  # Batch 2: 0.05 / 20
    approx(tl.batch_alpha(20, 5), 0.002)  # a 5-idea batch after 20 trials: 0.05 / 25
    approx(tl.batch_alpha(10, 1), 0.05 / 11)
    assert tl.batch_alpha(10, 10) < tl.batch_alpha(0, 10)
    raises(ValueError, tl.batch_alpha, 10, 0)


def test_seeded_registry_has_ten_rejected_ideas_and_ten_trials():
    p, td = tmp_paths()
    with td:
        rows = reg.load(p)
        assert [r["id"] for r in rows] == [f"B1-{i:02d}" for i in range(1, 11)]
        assert all(r["status"] == "rejected" and r["verdict"] == "REJECT" for r in rows)
        assert tl.total_trials(p) == 10
        approx(tl.next_batch_alpha(10, p), 0.0025)
        assert reg.problems(p) == []
        r1 = reg.get("B1-01", p)  # Task 5 numbers carried over unchanged
        assert r1["dev_stats"]["n_trades"] == 90
        approx(r1["dev_stats"]["mean_net"], 0.004771340330863635, 1e-15)
        approx(r1["dev_stats"]["boot_p"], 0.022797720227977204, 1e-15)
        assert "SIP" in r1["story"] and r1["cost"] == 0.001 and r1["rule"]["kind"] == "batch1"
        raises(reg.RegistryError, reg.seed_batch1, p)  # seeding is once only


def test_real_checked_in_registry_and_ledger_are_consistent():
    assert reg.problems() == []
    assert tl.total_trials() >= 10 and len(reg.load()) >= 10  # grows as batches are run; Batch 1 is the first 10
    assert all(r["status"] == "rejected" for r in reg.load() if r["batch"] == 1)
    # the 10 Batch 1 verdicts equal the Task 5 ledger line for line
    old = [json.loads(x) for x in (cfg.IDEAS / "ledger_ideas.jsonl").read_text().splitlines()]
    for o, r in zip(old, reg.load()[:10]):
        assert r["verdict"] == o["verdict"] and r["dev_stats"]["n_trades"] == o["n_trades"]


def test_ledger_detects_edit_deletion_and_reorder():
    p, td = tmp_paths()
    with td:
        n = tl.verify(p)
        lines = p.ledger.read_text().splitlines()
        p.ledger.write_text("\n".join(lines).replace('"verdict": "REJECT"', '"verdict": "SURVIVES"', 1) + "\n")
        raises(tl.LedgerTampered, tl.verify, p)
        p.ledger.write_text("\n".join(lines[:3] + lines[4:]) + "\n")  # one line removed
        raises(tl.LedgerTampered, tl.verify, p)
        p.ledger.write_text("\n".join(lines[:2] + [lines[3], lines[2]] + lines[4:]) + "\n")  # reordered
        raises(tl.LedgerTampered, tl.verify, p)
        p.ledger.write_text("\n".join(lines) + "\n")
        assert tl.verify(p) == n
        tl.append({"event": "note", "text": "x"}, p)  # append still fine on an intact ledger
        assert tl.verify(p) == n + 1


# ------------------------------------------------------------------ registry rules
def test_status_moves_are_enforced_and_logged():
    p, td = tmp_paths()
    with td:
        reg.register("B2-01", 2, "a", "s", STRONG, paths=p)
        raises(reg.RegistryError, reg.set_status, "B2-01", "forward", "skip a step", p)
        reg.set_status("B2-01", "tested", "run", p)
        reg.set_status("B2-01", "forward", "passed", p, forward_since="2026-11-01")
        raises(reg.RegistryError, reg.set_status, "B2-01", "tested", "back", p)
        reg.set_status("B2-01", "promoted", "ok", p)
        reg.set_status("B2-01", "retired", "bad", p)
        raises(reg.RegistryError, reg.set_status, "B2-01", "promoted", "no way back", p)
        raises(reg.RegistryError, reg.set_status, "B1-01", "forward", "a rejected idea stays rejected", p)
        assert reg.problems(p) == []
        assert [e["to"] for e in tl.events("status", p)] == ["tested", "forward", "promoted", "retired"]


def test_duplicate_variant_batch_size_and_id_rules():
    p, td = tmp_paths()
    with td:
        reg.register("B2-01", 2, "a", "s", STRONG, paths=p)
        raises(reg.RegistryError, reg.register, "B2-02", 2, "same", "s", dict(STRONG), paths=p)  # identical rule
        variant = json.loads(json.dumps(STRONG))
        variant["conditions"][0]["value"] = -0.01  # only a threshold changed
        msg = raises(reg.RegistryError, reg.register, "B2-02", 2, "tweak", "s", variant, paths=p)
        assert "variant" in msg and "NEW trial" in msg
        r = reg.register("B2-02", 2, "tweak", "s", variant, allow_variant=True, paths=p)
        assert r["variant_of"] == ["B2-01"]
        raises(reg.RegistryError, reg.register, "B3-01", 2, "x", "s", NOISE, paths=p)  # id must match the batch
        raises(reg.RegistryError, reg.register, "B2-01", 2, "dup id", "s", NOISE, paths=p)
        for k in range(3, 11):
            r = json.loads(json.dumps(NOISE))
            r["conditions"][0]["value"] = k
            reg.register(f"B2-{k:02d}", 2, f"n{k}", "s", r, allow_variant=True, paths=p)
        assert len(reg.batch_of(2, p)) == 10
        extra = json.loads(json.dumps(GAP))
        raises(reg.RegistryError, reg.register, "B2-11", 2, "11th", "s", extra, paths=p)  # at most 10 per batch
        raises(rules.RuleError, reg.register, "B4-01", 4, "bad", "s", {"kind": "daily"}, paths=p)  # rule is validated at registration


def test_registry_detects_edited_rule_and_status():
    p, td = tmp_paths()
    with td:
        reg.register("B2-01", 2, "a", "s", STRONG, paths=p)
        rows = reg.load(p)
        rows[-1]["rule"]["conditions"][0]["value"] = -0.05  # edit the rule but keep the stored hash
        reg._save(rows, p)
        assert any("rule edited" in x or "no longer matches" in x for x in reg.problems(p))
        rows[-1]["rule_hash"] = rules.rule_hash(rows[-1]["rule"])  # edit the hash too: the ledger copy still disagrees
        reg._save(rows, p)
        assert any("differs from the ledger" in x for x in reg.problems(p))
    p2, td2 = tmp_paths()
    with td2:
        rows = reg.load(p2)
        rows[0]["status"] = "forward"  # quietly flipping a rejected idea to forward
        reg._save(rows, p2)
        assert any("status" in x for x in reg.problems(p2))


# ------------------------------------------------------------------ rule engine: hand-computed
def tiny():
    return pd.DataFrame({"date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]),
                         "open": [100.0, 100.0, 98.0, 99.0, 101.0, 100.0], "close": [100.0, 97.0, 99.0, 100.0, 100.0, 103.0]})


def test_daily_rule_hand_computed():
    # ret_1d <= -2%: row 1 (97/100-1 = -3%). Long next open (98) to next close (99).
    rule = {"kind": "daily", "conditions": [{"feature": "ret_1d", "op": "<=", "value": -0.02}], "direction": {"fixed": 1},
            "entry": {"day": 1, "px": "open"}, "exit": {"day": 1, "px": "close"}}
    sc = rules.scan(rule, tiny())
    assert list(sc["signal_date"].dt.strftime("%d")) == ["02", "03", "04", "05"]  # rows 1..4 are priceable (need ret_1d and a next row)
    t = sc[sc["triggered"]]
    assert len(t) == 1 and str(t["entry_date"].iloc[0])[:10] == "2024-01-03"
    approx(t["gross"].iloc[0], 99 / 98 - 1, 1e-15)
    approx(float((t["direction"] * t["gross"]).iloc[0]) - 0.001, 99 / 98 - 1 - 0.001, 1e-15)
    # gross of every start (the random-entry pool) by hand: rows 1..4 -> C[i+1]/O[i+1]-1
    for g, e in zip(sc["gross"].values, [99 / 98 - 1, 100 / 99 - 1, 100 / 101 - 1, 103 / 100 - 1]):
        approx(g, e, 1e-15)


def test_gap_fade_direction_and_three_day_hold_hand_computed():
    d = tiny()
    sc = rules.scan(GAP, d)  # gap_next = O[i+1]/C[i]-1: -0%, 98/97-1=+1.03%, 99/99-1=0, 101/100-1=+1%, 100/100-1=0
    t = sc[sc["triggered"]]
    assert list(t["direction"]) == [-1.0, -1.0]  # both gaps are up -> fade = short
    approx(t["gross"].iloc[0], 99 / 98 - 1, 1e-15)  # row 1: entry O[2]=98, exit C[2]=99
    approx(t["gross"].iloc[1], 100 / 101 - 1, 1e-15)  # row 3: entry O[4]=101, exit C[4]=100
    approx((t["direction"] * t["gross"]).iloc[1], -(100 / 101 - 1), 1e-15)
    hold3 = {"kind": "daily", "conditions": [{"feature": "weekday", "op": ">=", "value": 0}], "direction": {"fixed": 1},
             "entry": {"day": 0, "px": "close"}, "exit": {"day": 3, "px": "close"}}
    s3 = rules.scan(hold3, d)
    assert len(s3) == 3  # rows 0,1,2 have an exit 3 rows later
    approx(s3["gross"].iloc[0], 100 / 100 - 1, 1e-15)
    approx(s3["gross"].iloc[1], 100 / 97 - 1, 1e-15)
    approx(s3["gross"].iloc[2], 103 / 99 - 1, 1e-15)
    assert str(s3["exit_date"].iloc[2])[:10] == "2024-01-08"


def test_threshold_exactly_at_the_line_triggers_like_task5():
    d = pd.DataFrame({"date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]), "open": [100.0, 98.0, 98.0], "close": [100.0, 98.0, 99.0]})
    rule = {"kind": "daily", "conditions": [{"feature": "ret_1d", "op": "<=", "value": -0.02}], "direction": {"fixed": 1},
            "entry": {"day": 1, "px": "open"}, "exit": {"day": 1, "px": "close"}}
    assert bool(rules.scan(rule, d)["triggered"].iloc[0])  # 98/100-1 = -0.02000000000000002 still counts as "down 2%"
    strict = dict(rule, conditions=[{"feature": "ret_1d", "op": "<", "value": -0.02}])
    assert not bool(rules.scan(strict, d)["triggered"].iloc[0])


def test_validation_refuses_lookahead_and_junk():
    ok = json.loads(json.dumps(STRONG))
    rules.validate_rule(ok)
    bad = [dict(ok, entry={"day": 0, "px": "open"}),  # entering before the signal is known
           dict(ok, exit={"day": 1, "px": "open"}),  # exit before entry
           dict(ok, extra=1), dict(ok, kind="weekly"),
           dict(ok, conditions=[{"feature": "future_ret_5d", "op": ">", "value": 0}]),
           dict(ok, conditions=[{"feature": "ret_30d", "op": ">", "value": 0}]),
           dict(ok, conditions=[{"feature": "ret_1d", "op": "~", "value": 0}]),
           dict(ok, conditions=[{"feature": "ret_1d", "op": ">", "value": float("nan")}]),
           dict(ok, conditions=[]), dict(ok, direction={"fixed": 2}), dict(ok, direction={"with": "nope"}),
           dict(GAP, entry={"day": 0, "px": "close"}),  # gap_next is only known at the next open
           {"kind": "intraday", "signal": {"from": "o:0915", "to": "c:0940"}, "conditions": [{"feature": "sig_ret", "op": "!=", "value": 0}],
            "direction": {"with": "sig_ret"}, "entry": "o:0935", "exit": "o:1515"},  # enters before the signal window ends
           {"kind": "intraday", "signal": {"from": "o:0915", "to": "c:0940"}, "conditions": [{"feature": "sig_ret", "op": "!=", "value": 0}],
            "direction": {"with": "sig_ret"}, "entry": "o:0945", "exit": "o:0945"}]
    for r in bad:
        raises(rules.RuleError, rules.validate_rule, r)


def test_hash_ignores_key_order_and_family_ignores_numbers():
    a = {"kind": "daily", "conditions": [{"feature": "ret_1d", "op": "<=", "value": -0.02}], "direction": {"fixed": 1}, "entry": {"day": 1, "px": "open"}, "exit": {"day": 1, "px": "close"}}
    b = {"exit": {"px": "close", "day": 1}, "entry": {"px": "open", "day": 1}, "direction": {"fixed": 1}, "conditions": [{"value": -0.02, "op": "<=", "feature": "ret_1d"}], "kind": "daily"}
    assert rules.rule_hash(a) == rules.rule_hash(b)
    c = json.loads(json.dumps(a))
    c["conditions"][0]["value"] = -0.021
    assert rules.rule_hash(c) != rules.rule_hash(a) and rules.family_hash(c) == rules.family_hash(a)
    assert rules.family_hash(GAP) != rules.family_hash(a)


# ------------------------------------------------------------------ no lookahead, and equal to Task 5
def test_no_lookahead_truncating_or_scrambling_the_future_changes_nothing():
    d, v = make_daily(300, vix=True, seed=5)
    vr = {"kind": "daily", "conditions": [{"feature": "vix_chg_1d", "op": ">=", "value": 0.05}, {"feature": "ret_5d", "op": "<", "value": 0.0}],
          "direction": {"with": "ret_1d"}, "entry": {"day": 0, "px": "close"}, "exit": {"day": 2, "px": "close"}}
    for rule in (STRONG, GAP, vr):
        full = rules.scan(rule, d, v)
        for k in (100, 180, 250):
            cut = d["date"].iloc[k]
            part = rules.scan(rule, d[d["date"] <= cut], v[v["date"] <= cut])
            ref = full[full["exit_date"] <= cut].reset_index(drop=True)
            pd.testing.assert_frame_equal(part, ref)
            mess = d.copy()  # scramble everything after row k: signals of finished trades must not move
            mess.loc[mess.index > k, ["open", "close"]] = 1.0
            vm = v.copy()
            vm.loc[vm.index > k, "close"] = 1.0
            part2 = rules.scan(rule, mess, vm)
            ref2 = full[full["exit_date"] <= cut].reset_index(drop=True)
            pd.testing.assert_frame_equal(part2[part2["exit_date"] <= cut].reset_index(drop=True), ref2)
    m = make_5min(30)
    ir = {"kind": "intraday", "signal": {"from": "o:0915", "to": "c:0940"}, "conditions": [{"feature": "sig_ret", "op": "!=", "value": 0}],
          "direction": {"with": "sig_ret"}, "entry": "o:0945", "exit": "o:1515"}
    full = rules.scan(ir, m5=m)
    day = full["signal_date"].iloc[15]
    mm = m.copy()
    mm.loc[(mm["date"].dt.normalize() == day) & (mm["date"].dt.strftime("%H%M") >= "0945"), ["open", "close"]] = 1.0  # change prices AFTER the signal
    after = rules.scan(ir, m5=mm)
    a, b = full[full["signal_date"] == day].iloc[0], after[after["signal_date"] == day].iloc[0]
    assert a["triggered"] == b["triggered"] and a["direction"] == b["direction"]  # the signal reads only 09:15-09:40


def test_dsl_reproduces_task5_ideas_on_the_same_data():
    d, v = make_daily(900, vix=True, seed=3)
    d.loc[d.index % 37 == 0, "close"] *= 0.97  # force some big drops / gaps / vix spikes so every idea trades
    v.loc[v.index % 41 == 0, "close"] *= 1.3
    m = make_5min(60, seed=4)

    def same(t5, rule, data, label, use_entry_date=True):
        sc = rules.scan(rule, **data)
        t = sc[sc["triggered"]]
        assert len(t) == len(t5.gross) > 0, (label, len(t), len(t5.gross))
        np.testing.assert_allclose(t["gross"].values, t5.gross, rtol=0, atol=1e-15, err_msg=label)
        np.testing.assert_array_equal(t["direction"].values, t5.direction, err_msg=label)
        np.testing.assert_array_equal(t["entry_date"].values.astype("datetime64[D]"), t5.entry_date, err_msg=label)

    ge = lambda f, v_: {"feature": f, "op": ">=", "value": v_}  # noqa: E731
    same(fi.idea2_overnight(d), {"kind": "daily", "conditions": [ge("weekday", 0)], "direction": {"fixed": 1},
                                 "entry": {"day": 0, "px": "close"}, "exit": {"day": 1, "px": "open"}}, {"daily": d}, "idea2")
    same(fi.idea3_gap_fade(d), GAP, {"daily": d}, "idea3")
    same(fi.idea4_forced_sellers(d), {"kind": "daily", "conditions": [{"feature": "ret_1d", "op": "<=", "value": -0.02}], "direction": {"fixed": 1},
                                      "entry": {"day": 1, "px": "open"}, "exit": {"day": 1, "px": "close"}}, {"daily": d}, "idea4")
    same(fi.idea5_vix_panic(d, v), {"kind": "daily", "conditions": [ge("vix_chg_1d", 0.15)], "direction": {"fixed": 1},
                                    "entry": {"day": 0, "px": "close"}, "exit": {"day": 3, "px": "close"}}, {"daily": d, "vix": v}, "idea5")
    same(fi.idea6_closing(m), {"kind": "intraday", "signal": {"from": "o:1415", "to": "o:1515"}, "conditions": [{"feature": "sig_ret", "op": "!=", "value": 0}],
                               "direction": {"with": "sig_ret"}, "entry": "o:1515", "exit": "c:1525"}, {"m5": m}, "idea6")
    same(fi.idea7_morning(m), {"kind": "intraday", "signal": {"from": "o:0915", "to": "c:0940"}, "conditions": [{"feature": "sig_ret", "op": "!=", "value": 0}],
                               "direction": {"with": "sig_ret"}, "entry": "o:0945", "exit": "o:1515"}, {"m5": m}, "idea7")


def test_to_trades_feeds_the_task5_statistics():
    d, _ = make_daily(600, seed=9)
    t = rules.to_trades(2, "x", rules.scan(STRONG, d))
    assert t.cand[1].shape[0] == 598  # every start with a prior-day return and a next row
    assert (t.hold == 1).all() and len(t.gross) == len(t.direction) > 100
    approx(float(t.net(0.001).mean()), float((t.direction * t.gross).mean() - 0.001), 1e-15)
    assert fi.null_p(t, 0.001, n_draw=500)[0] < 0.05  # the built-in edge is picked up by the Task 5 random-entry null


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except Exception as e:  # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(e))
    print("all passed" if not fails else f"{fails} FAILED")
    sys.exit(1 if fails else 0)
