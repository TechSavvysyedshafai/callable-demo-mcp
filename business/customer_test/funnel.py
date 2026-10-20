"""Funnel analysis for the Shop Starter Kit test (rules in EXPERIMENT_PLAN.md).

events.csv columns: date,channel,event[,price_choice]
  event: visit | signup | price_intent  (price_intent rows carry price_choice: free | 299 | 999 | 2999)
A signup row is counted only if the person ticked the consent box (the page does not send the event otherwise).

Usage: python3 funnel.py events.csv
"""

from __future__ import annotations

import csv
import math
import sys
from collections import Counter, defaultdict

PASS_SIGNUP_RATE = 0.08
PASS_PAID_SHARE = 0.25
FAIL_SIGNUP_RATE = 0.03
FAIL_PAID_SHARE = 0.10
MIN_VISITS = 300
PAID = {"299", "999", "2999"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion k/n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def load(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarise(rows: list[dict]) -> dict:
    visits = sum(1 for r in rows if r["event"] == "visit")
    signups = sum(1 for r in rows if r["event"] == "signup")
    choices = Counter((r.get("price_choice") or "").strip() for r in rows if r["event"] == "price_intent")
    n_choice = sum(choices.values())
    paid = sum(v for k, v in choices.items() if k in PAID)
    return {"visits": visits, "signups": signups, "price_choices": n_choice, "paid": paid, "choices": dict(choices)}


def verdict(s: dict, extended: bool = False) -> tuple[str, str]:
    """Pre-registered rule. Uses signups as the base for the paid share when price choices are missing."""
    if s["visits"] < MIN_VISITS:
        return ("INCONCLUSIVE", f"only {s['visits']} visits, need {MIN_VISITS}" + ("" if extended else " (extend once by 7 days)"))
    rate = s["signups"] / s["visits"]
    base = s["price_choices"] or s["signups"]
    share = (s["paid"] / base) if base else 0.0
    if rate >= PASS_SIGNUP_RATE and share >= PASS_PAID_SHARE:
        return ("PASS", f"signup rate {rate:.1%} and paid share {share:.1%} both meet the bar")
    if rate < FAIL_SIGNUP_RATE or share < FAIL_PAID_SHARE:
        return ("FAIL", f"signup rate {rate:.1%} or paid share {share:.1%} is below the stop line")
    return ("CHANGE ONE THING", f"signup rate {rate:.1%}, paid share {share:.1%}: in between. Change copy or channel, run 7 more days, then decide")


def report(rows: list[dict]) -> str:
    out = []
    by_ch = defaultdict(list)
    for r in rows:
        by_ch[r["channel"] or "unknown"].append(r)
    s = summarise(rows)
    out.append(f"ALL CHANNELS: visits {s['visits']}, signups {s['signups']}, price answers {s['price_choices']}, paid choices {s['paid']}")
    lo, hi = wilson(s["signups"], s["visits"])
    out.append(f"  signup rate {s['signups'] / s['visits']:.1%} (95% range {lo:.1%} to {hi:.1%})" if s["visits"] else "  no visits yet")
    if s["price_choices"]:
        lo, hi = wilson(s["paid"], s["price_choices"])
        out.append(f"  paid share {s['paid'] / s['price_choices']:.1%} (95% range {lo:.1%} to {hi:.1%}); choices {s['choices']}")
    out.append("BY CHANNEL (signups / visits):")
    for ch, rr in sorted(by_ch.items()):
        c = summarise(rr)
        rate = f"{c['signups'] / c['visits']:.1%}" if c["visits"] else "n/a"
        out.append(f"  {ch}: {c['signups']}/{c['visits']} = {rate}")
    v, why = verdict(s)
    out.append(f"VERDICT: {v}: {why}")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(report(load(sys.argv[1])))
