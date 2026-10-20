"""Consent-first messenger. Safe by design: dry run by default, no live sending.

A contact gets a message ONLY if all of these hold:
  - consent == "yes" and a consent_date and consent_source are recorded
  - not opted out
  - the phone number is valid (E.164, e.g. +919876543210) and not a duplicate in this run
  - the last message was at least WEEKLY_CAP_DAYS days ago
  - the send time is inside quiet-hours-allowed window (09:00-20:00 India time)
  - the per-run limit has not been reached
Every message gets an opt-out line. Replies containing STOP words mark the contact opted out.

Contacts CSV columns: phone,name,consent,consent_date,consent_source,opted_out,language,last_sent
Provider interface: send(phone, text) -> (ok: bool, info: str). Only DryRunProvider and OutboxProvider ship here;
a live provider (WhatsApp Cloud API, SMS) is NOT included and must be added and tested separately.
"""

from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
WEEKLY_CAP_DAYS = 7
SEND_START_HOUR, SEND_END_HOUR = 9, 20  # sends allowed from 09:00 up to 19:59 IST
MAX_PER_RUN = 50
OPT_OUT_LINE = {"en": "Reply STOP to stop these messages.", "hi": "ये संदेश बंद करने के लिए STOP लिखें।"}
STOP_WORDS = {"stop", "unsubscribe", "cancel", "end", "quit", "बंद", "रोको", "रुको", "बंद करो", "नहीं चाहिए"}
E164 = re.compile(r"^\+[1-9]\d{9,14}$")
FIELDS = ["phone", "name", "consent", "consent_date", "consent_source", "opted_out", "language", "last_sent"]


@dataclass
class Contact:
    phone: str
    name: str
    consent: str
    consent_date: str
    consent_source: str
    opted_out: str
    language: str
    last_sent: str


def load_contacts(path: Path) -> list[Contact]:
    with Path(path).open(newline="", encoding="utf-8") as f:
        return [Contact(**{k: (r.get(k) or "").strip() for k in FIELDS}) for r in csv.DictReader(f)]


def save_contacts(path: Path, contacts: list[Contact]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for c in contacts:
            w.writerow({k: getattr(c, k) for k in FIELDS})


def normalise_phone(raw: str) -> str:
    """Indian 10-digit numbers get +91; a leading 0 is dropped. Returns '' if the result is not valid E.164."""
    s = re.sub(r"[\s\-()]", "", raw or "")
    if re.fullmatch(r"0?[6-9]\d{9}", s):
        s = "+91" + s[-10:]
    return s if E164.match(s) else ""


def is_stop(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in STOP_WORDS or t.rstrip(".!") in STOP_WORDS


def render(template: str, name: str, extra: dict | None = None) -> str:
    """Fill {name} and any {key} in extra. A missing key is an error, never a blank."""
    values = {"name": name or "there", **(extra or {})}
    try:
        return template.format(**values)
    except KeyError as e:
        raise ValueError(f"template needs a value for {e}") from None


def with_opt_out(text: str, language: str) -> str:
    line = OPT_OUT_LINE.get(language, OPT_OUT_LINE["en"])
    return text if "STOP" in text else text.rstrip() + " " + line


def in_send_window(now: datetime) -> bool:
    n = now.astimezone(IST)
    return SEND_START_HOUR <= n.hour < SEND_END_HOUR


def skip_reason(c: Contact, now: datetime, seen: set[str]) -> str | None:
    if c.consent.lower() != "yes" or not c.consent_date or not c.consent_source:
        return "no_consent_record"
    if c.opted_out.lower() in {"1", "yes", "true"}:
        return "opted_out"
    p = normalise_phone(c.phone)
    if not p:
        return "invalid_phone"
    if p in seen:
        return "duplicate_in_run"
    if c.last_sent:
        try:
            last = datetime.fromisoformat(c.last_sent)
        except ValueError:
            return "bad_last_sent"
        if last.tzinfo is None:
            last = last.replace(tzinfo=IST)
        if now - last < timedelta(days=WEEKLY_CAP_DAYS):
            return "weekly_cap"
    return None


class DryRunProvider:
    """Prints what WOULD be sent. Nothing leaves this machine."""

    def send(self, phone: str, text: str):
        print(f"[dry-run] to {phone}: {text}")
        return True, "dry-run"


class OutboxProvider:
    """Appends to an outbox CSV that a person reviews and sends by hand or uploads to a tool."""

    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.exists():
            self.path.write_text("phone,text\n", encoding="utf-8")

    def send(self, phone: str, text: str):
        with self.path.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([phone, text])
        return True, "outbox"


def run(contacts: list[Contact], template_by_lang: dict[str, str], provider, now: datetime | None = None,
        max_per_run: int = MAX_PER_RUN, extra: dict | None = None, mark_sent: bool = True) -> dict:
    """Returns {"sent": [...], "skipped": {reason: count}}. Updates last_sent on contacts when mark_sent."""
    now = now or datetime.now(IST)
    out = {"sent": [], "skipped": {}}
    if not in_send_window(now):
        out["skipped"]["outside_send_window"] = len(contacts)
        return out
    seen: set[str] = set()
    for c in contacts:
        reason = skip_reason(c, now, seen)
        if reason is None and len(out["sent"]) >= max_per_run:
            reason = "per_run_limit"
        if reason:
            out["skipped"][reason] = out["skipped"].get(reason, 0) + 1
            continue
        lang = c.language if c.language in template_by_lang else "en"
        text = with_opt_out(render(template_by_lang[lang], c.name, extra), lang)
        phone = normalise_phone(c.phone)
        ok, info = provider.send(phone, text)
        if ok:
            seen.add(phone)
            out["sent"].append(phone)
            if mark_sent:
                c.last_sent = now.astimezone(IST).isoformat(timespec="seconds")
        else:
            out["skipped"]["provider_error"] = out["skipped"].get("provider_error", 0) + 1
    return out


def process_replies(contacts: list[Contact], replies: list[tuple[str, str]]) -> int:
    """replies = [(phone, text)]. Any STOP word marks that contact opted out. Returns how many were opted out."""
    by_phone = {normalise_phone(c.phone): c for c in contacts}
    n = 0
    for phone, text in replies:
        c = by_phone.get(normalise_phone(phone))
        if c is not None and is_stop(text) and c.opted_out.lower() not in {"1", "yes", "true"}:
            c.opted_out = "1"
            n += 1
    return n


def main(argv: list[str]) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Consent-first messenger (dry run unless --outbox is given)")
    ap.add_argument("contacts_csv")
    ap.add_argument("templates_json", help='{"en": "Hi {name}, ...", "hi": "..."}')
    ap.add_argument("--outbox", help="write approved messages to this CSV instead of printing")
    ap.add_argument("--replies", help="CSV phone,text of incoming replies to process first")
    ap.add_argument("--max", type=int, default=MAX_PER_RUN)
    ap.add_argument("--save", action="store_true", help="write updated contacts (last_sent, opt-outs) back")
    a = ap.parse_args(argv)
    contacts = load_contacts(Path(a.contacts_csv))
    if a.replies:
        with open(a.replies, newline="", encoding="utf-8") as f:
            reps = [(r["phone"], r["text"]) for r in csv.DictReader(f)]
        print("opted out from replies:", process_replies(contacts, reps))
    templates = json.loads(Path(a.templates_json).read_text(encoding="utf-8"))
    provider = OutboxProvider(Path(a.outbox)) if a.outbox else DryRunProvider()
    res = run(contacts, templates, provider, max_per_run=a.max, mark_sent=bool(a.outbox))
    print("sent:", len(res["sent"]), "skipped:", res["skipped"])
    if a.save:
        save_contacts(Path(a.contacts_csv), contacts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
