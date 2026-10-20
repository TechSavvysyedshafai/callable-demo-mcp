import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import funnel as f  # noqa: E402


def rows(visits, signups, paid, free=0, ch="linkedin"):
    r = [{"date": "d", "channel": ch, "event": "visit"} for _ in range(visits)]
    r += [{"date": "d", "channel": ch, "event": "signup"} for _ in range(signups)]
    r += [{"date": "d", "channel": ch, "event": "price_intent", "price_choice": "299"} for _ in range(paid)]
    r += [{"date": "d", "channel": ch, "event": "price_intent", "price_choice": "free"} for _ in range(free)]
    return r


def t_wilson_known_values():
    lo, hi = f.wilson(50, 100)
    assert abs(lo - 0.4038) < 1e-3 and abs(hi - 0.5962) < 1e-3, (lo, hi)
    assert f.wilson(0, 0) == (0.0, 1.0)
    lo, hi = f.wilson(0, 10)
    assert lo == 0.0 and 0.25 < hi < 0.32


def t_pass():
    s = f.summarise(rows(400, 40, 10, free=30))  # 10% signup, 25% paid
    assert f.verdict(s)[0] == "PASS", f.verdict(s)


def t_fail_low_signup():
    s = f.summarise(rows(400, 8, 4, free=4))  # 2% signup
    assert f.verdict(s)[0] == "FAIL"


def t_fail_low_paid():
    s = f.summarise(rows(400, 40, 3, free=37))  # 7.5% paid share
    assert f.verdict(s)[0] == "FAIL"


def t_in_between():
    s = f.summarise(rows(400, 20, 3, free=17))  # 5% signup, 15% paid
    assert f.verdict(s)[0] == "CHANGE ONE THING"


def t_inconclusive_few_visits():
    s = f.summarise(rows(120, 30, 20, free=10))
    v = f.verdict(s)
    assert v[0] == "INCONCLUSIVE" and "120" in v[1]


def t_boundaries():
    s = f.summarise(rows(300, 24, 6, free=18))  # exactly 8% and exactly 25%
    assert f.verdict(s)[0] == "PASS"
    s = f.summarise(rows(300, 9, 3, free=6))  # exactly 3% (not below) and 33% paid
    assert f.verdict(s)[0] == "CHANGE ONE THING"


def t_report_runs_and_channels():
    r = rows(200, 10, 3, free=7, ch="a") + rows(200, 20, 6, free=14, ch="b")
    txt = f.report(r)
    assert "a: 10/200 = 5.0%" in txt and "b: 20/200 = 10.0%" in txt and "VERDICT" in txt


def t_missing_price_answers_use_signups_as_base():
    s = f.summarise(rows(400, 40, 0))
    assert s["price_choices"] == 0 and f.verdict(s)[0] == "FAIL"  # paid share 0 of 40


if __name__ == "__main__":
    n = 0
    for k, v in sorted(globals().items()):
        if k.startswith("t_") and callable(v):
            v()
            n += 1
    print(f"funnel tests passed: {n}")
