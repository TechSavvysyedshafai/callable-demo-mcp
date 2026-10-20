import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import messenger as m  # noqa: E402

NOON = datetime(2026, 10, 21, 12, 0, tzinfo=m.IST)
T = {"en": "Hi {name}, new stock is in.", "hi": "नमस्ते {name}, नया स्टॉक आ गया है।"}


class Cap:
    def __init__(self):
        self.sent = []

    def send(self, phone, text):
        self.sent.append((phone, text))
        return True, "ok"


def mk(phone="+919876543210", consent="yes", cd="2026-10-01", cs="counter_form", opt="", lang="en", last="", name="Ravi"):
    return m.Contact(phone, name, consent, cd, cs, opt, lang, last)


def t_consent_required():
    for c in (mk(consent="no"), mk(consent=""), mk(cd=""), mk(cs="")):
        p = Cap()
        r = m.run([c], T, p, now=NOON)
        assert not p.sent and r["skipped"] == {"no_consent_record": 1}, r


def t_opted_out_blocked():
    p = Cap()
    r = m.run([mk(opt="1")], T, p, now=NOON)
    assert not p.sent and r["skipped"] == {"opted_out": 1}


def t_phone_validation_and_normalise():
    assert m.normalise_phone("9540833550") == "+919540833550"
    assert m.normalise_phone("09540833550") == "+919540833550"
    assert m.normalise_phone("+91 95408 33550") == "+919540833550"
    assert m.normalise_phone("12345") == ""
    assert m.normalise_phone("5555555555") == ""  # not an Indian mobile pattern, no +country
    assert m.normalise_phone("+15553555472") == "+15553555472"  # valid E.164 shape


def t_duplicate_in_run():
    p = Cap()
    r = m.run([mk(), mk(phone="09876543210")], T, p, now=NOON)
    assert len(p.sent) == 1 and r["skipped"] == {"duplicate_in_run": 1}, r


def t_weekly_cap():
    p = Cap()
    recent = (NOON - timedelta(days=3)).isoformat()
    old = (NOON - timedelta(days=8)).isoformat()
    r = m.run([mk(last=recent), mk(phone="+919876543211", last=old)], T, p, now=NOON)
    assert len(p.sent) == 1 and r["skipped"] == {"weekly_cap": 1}, r
    exactly7 = (NOON - timedelta(days=7)).isoformat()
    p2 = Cap()
    m.run([mk(last=exactly7)], T, p2, now=NOON)
    assert len(p2.sent) == 1


def t_quiet_hours():
    for h, ok in ((8, False), (9, True), (19, True), (20, False), (23, False)):
        p = Cap()
        now = NOON.replace(hour=h)
        m.run([mk()], T, p, now=now)
        assert bool(p.sent) == ok, h


def t_stop_words_and_replies():
    for s in ("STOP", " stop ", "Stop.", "बंद", "UNSUBSCRIBE", "रोको"):
        assert m.is_stop(s), s
    for s in ("stop by the shop tomorrow?", "yes", "price?", ""):
        assert not m.is_stop(s), s
    cs = [mk(), mk(phone="+919876543211")]
    n = m.process_replies(cs, [("9876543210", "STOP"), ("+919876543211", "hello"), ("+919999999999", "stop")])
    assert n == 1 and cs[0].opted_out == "1" and cs[1].opted_out == ""
    p = Cap()
    m.run(cs, T, p, now=NOON)
    assert [x[0] for x in p.sent] == ["+919876543211"]


def t_opt_out_line_and_language():
    p = Cap()
    m.run([mk(lang="hi")], T, p, now=NOON)
    assert p.sent[0][1].endswith(m.OPT_OUT_LINE["hi"]) and "नमस्ते Ravi" in p.sent[0][1]
    p2 = Cap()
    m.run([mk(lang="fr")], T, p2, now=NOON)  # unknown language falls back to English
    assert p2.sent[0][1].startswith("Hi Ravi") and p2.sent[0][1].endswith(m.OPT_OUT_LINE["en"])
    assert m.with_opt_out("Reply STOP to quit.", "en") == "Reply STOP to quit."


def t_render_missing_key_errors():
    try:
        m.render("Hi {name}, {offer}", "A")
        raise AssertionError("should fail")
    except ValueError as e:
        assert "offer" in str(e)
    assert m.render("Hi {name}, {offer}", "A", {"offer": "10%"}) == "Hi A, 10%"


def t_per_run_limit_and_last_sent_updated():
    cs = [mk(phone=f"+9198765432{i:02d}") for i in range(5)]
    p = Cap()
    r = m.run(cs, T, p, now=NOON, max_per_run=3)
    assert len(p.sent) == 3 and r["skipped"] == {"per_run_limit": 2}, r
    assert sum(1 for c in cs if c.last_sent) == 3
    p2 = Cap()
    r2 = m.run(cs, T, p2, now=NOON + timedelta(minutes=5), max_per_run=3)
    assert len(p2.sent) == 2 and r2["skipped"].get("weekly_cap") == 3, r2  # the 3 just messaged are capped


def t_dry_run_default_and_outbox(tmp=Path("/tmp/_msgr_test")):
    tmp.mkdir(exist_ok=True)
    ob = tmp / "outbox.csv"
    if ob.exists():
        ob.unlink()
    c = [mk()]
    m.run(c, T, m.DryRunProvider(), now=NOON, mark_sent=False)
    assert c[0].last_sent == "" and not ob.exists()
    m.run(c, T, m.OutboxProvider(ob), now=NOON)
    lines = ob.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "phone,text" and len(lines) == 2 and "+919876543210" in lines[1]


def t_save_and_load_roundtrip(tmp=Path("/tmp/_msgr_test")):
    tmp.mkdir(exist_ok=True)
    f = tmp / "c.csv"
    cs = [mk(), mk(phone="+919876543211", lang="hi", name="सीमा")]
    m.save_contacts(f, cs)
    back = m.load_contacts(f)
    assert [(c.phone, c.name, c.language) for c in back] == [(c.phone, c.name, c.language) for c in cs]


if __name__ == "__main__":
    n = 0
    for k, v in sorted(globals().items()):
        if k.startswith("t_") and callable(v):
            v()
            n += 1
    print(f"messenger tests passed: {n}")
