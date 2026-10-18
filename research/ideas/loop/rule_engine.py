"""Machine-readable trading rules for new ideas, and the scanner that turns a rule + data into trades.

A rule is plain JSON (so it can be hashed and cannot hide logic in code). Two kinds:

 daily:    {"kind":"daily","conditions":[{"feature":"ret_1d","op":"<=","value":-0.02}],
            "direction":{"fixed":1} | {"with":"ret_1d"} | {"against":"gap_next"},
            "entry":{"day":1,"px":"open"}, "exit":{"day":1,"px":"close"}}
           The signal is read at the CLOSE of row i (day 0). "day" counts trading rows after row i.
           features: ret_Nd, vix_chg_Nd (N=1..20), vix_level, gap_next (open of day 1 / close of day 0 - 1; needs entry >= day-1 open), weekday (0=Mon).
 intraday: {"kind":"intraday","signal":{"from":"o:0915","to":"c:0940"},"conditions":[{"feature":"sig_ret","op":"!=","value":0}],
            "direction":{"with":"sig_ret"}, "entry":"o:0945", "exit":"o:1515"}
           "o:HHMM" = open of the 5-minute bar labelled HHMM, "c:HHMM" = its close (HHMM + 5 minutes). Entry must not be before the signal ends.

Same conventions as Task 5 (forced_trader_ideas.py): fills exactly at the stated print, cost is charged per round trip,
thresholds use the same 1e-12 float tolerance. Dev data only; nothing here reads the hidden holdout or places orders.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date

import numpy as np
import pandas as pd

import loop_config as cfg

sys.path.insert(0, str(cfg.IDEAS))
import forced_trader_ideas as fi  # noqa: E402  (reused, never edited)

EPS = fi.EPS
OPS = {">", ">=", "<", "<=", "==", "!=", "abs_gt", "abs_ge"}
DAILY_KEYS = {"kind", "conditions", "direction", "entry", "exit"}
INTRA_KEYS = {"kind", "signal", "conditions", "direction", "entry", "exit"}
FEAT_RE = re.compile(r"^(ret|vix_chg)_(\d{1,2})d$")
PT_RE = re.compile(r"^([oc]):([01]\d|2[0-3])([0-5]\d)$")
SCAN_COLS = ["signal_date", "entry_date", "exit_date", "triggered", "direction", "gross"]


class RuleError(ValueError):
    pass


# ----------------------------------------------------------------------------------------------- hashing
def canon(o) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"))


def rule_hash(rule: dict) -> str:
    return hashlib.sha256(canon(rule).encode()).hexdigest()


def family_hash(rule: dict) -> str:
    """Same rule with every number blanked: two rules with the same family differ only in thresholds / hold lengths."""
    def blank(x):
        if isinstance(x, bool):
            return x
        if isinstance(x, (int, float)):
            return 0
        if isinstance(x, dict):
            return {k: blank(v) for k, v in x.items()}
        if isinstance(x, list):
            return [blank(v) for v in x]
        return x
    return hashlib.sha256(canon(blank(rule)).encode()).hexdigest()


# ----------------------------------------------------------------------------------------------- validation
def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and np.isfinite(x)


def _pt_minutes(p: str) -> int:
    m = PT_RE.match(p)
    if not m:
        raise RuleError(f"bad price point {p!r}; use o:HHMM or c:HHMM")
    return int(m.group(2)) * 60 + int(m.group(3)) + (5 if m.group(1) == "c" else 0)


def _check_conditions(conds, allowed) -> list:
    if not isinstance(conds, list) or not conds:
        raise RuleError("conditions must be a non-empty list")
    used = []
    for c in conds:
        if not isinstance(c, dict) or set(c) != {"feature", "op", "value"}:
            raise RuleError("each condition needs exactly feature, op, value")
        if c["op"] not in OPS or not _num(c["value"]):
            raise RuleError(f"bad condition {c}")
        if not allowed(c["feature"]):
            raise RuleError(f"unknown feature {c['feature']!r}")
        used.append(c["feature"])
    return used


def _daily_feature_ok(f: str) -> bool:
    m = FEAT_RE.match(f)
    if m:
        return 1 <= int(m.group(2)) <= 20
    return f in ("vix_level", "gap_next", "weekday")


def _check_direction(d, feats_ok) -> list:
    if not isinstance(d, dict) or len(d) != 1:
        raise RuleError("direction must be {fixed:+-1} or {with:feature} or {against:feature}")
    (k, v), = d.items()
    if k == "fixed":
        if v not in (1, -1) or isinstance(v, bool):
            raise RuleError("fixed direction must be 1 or -1")
        return []
    if k in ("with", "against") and feats_ok(v):
        return [v]
    raise RuleError(f"bad direction {d}")


def _order(pt) -> tuple:
    return (pt["day"], 0 if pt["px"] == "open" else 1)


def validate_rule(rule: dict) -> None:
    if not isinstance(rule, dict) or rule.get("kind") not in ("daily", "intraday"):
        raise RuleError("rule.kind must be 'daily' or 'intraday'")
    if rule["kind"] == "daily":
        if set(rule) != DAILY_KEYS:
            raise RuleError(f"daily rule keys must be exactly {sorted(DAILY_KEYS)}")
        used = _check_conditions(rule["conditions"], _daily_feature_ok)
        used += _check_direction(rule["direction"], _daily_feature_ok)
        for k in ("entry", "exit"):
            p = rule[k]
            if not (isinstance(p, dict) and set(p) == {"day", "px"} and isinstance(p["day"], int) and not isinstance(p["day"], bool)
                    and 0 <= p["day"] <= 20 and p["px"] in ("open", "close")):
                raise RuleError(f"bad {k}: {p}")
        e, x = _order(rule["entry"]), _order(rule["exit"])
        if e < (0, 1):
            raise RuleError("entry cannot be before the close of the signal day (the signal is read at that close)")
        if x <= e:
            raise RuleError("exit must be after entry")
        if "gap_next" in used and e < (1, 0):
            raise RuleError("gap_next is only known at the next open: entry must be day 1 open or later")
    else:
        if set(rule) != INTRA_KEYS:
            raise RuleError(f"intraday rule keys must be exactly {sorted(INTRA_KEYS)}")
        s = rule["signal"]
        if not (isinstance(s, dict) and set(s) == {"from", "to"}):
            raise RuleError("signal needs from and to")
        a, b = _pt_minutes(s["from"]), _pt_minutes(s["to"])
        if b <= a:
            raise RuleError("signal window must have positive length")
        ok = lambda f: f in ("sig_ret", "weekday")  # noqa: E731
        _check_conditions(rule["conditions"], ok)
        _check_direction(rule["direction"], ok)
        e, x = _pt_minutes(rule["entry"]), _pt_minutes(rule["exit"])
        if e < b:
            raise RuleError("entry is before the signal window ends (lookahead)")
        if x <= e or x > 15 * 60 + 30:
            raise RuleError("exit must be after entry and by 15:30")


def needs(rule: dict) -> dict:
    """What data the rule reads and how many daily rows of history its features need."""
    if rule["kind"] == "intraday":
        return {"daily": False, "vix": False, "m5": True, "lookback_rows": 0, "max_exit_day": 0}
    feats = [c["feature"] for c in rule["conditions"]] + list(rule["direction"].values())
    n = [int(m.group(2)) for f in feats if (m := FEAT_RE.match(str(f)))]
    return {"daily": True, "vix": any(str(f).startswith("vix_") for f in feats), "m5": False,
            "lookback_rows": max(n or [0]), "max_exit_day": rule["exit"]["day"]}


# ----------------------------------------------------------------------------------------------- features / conditions
def _cond(x: np.ndarray, op: str, v: float) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        if op == ">":
            return x > v + EPS
        if op == ">=":
            return x >= v - EPS
        if op == "<":
            return x < v - EPS
        if op == "<=":
            return x <= v + EPS
        if op == "==":
            return x == v
        if op == "!=":
            return x != v
        if op == "abs_gt":
            return np.abs(x) > v + EPS
        return np.abs(x) >= v - EPS


def _direction(rule: dict, F: dict, n: int) -> np.ndarray:
    (k, v), = rule["direction"].items()
    if k == "fixed":
        return np.full(n, float(v))
    s = np.sign(F[v])
    return s if k == "with" else -s


def _finish(rule, F, n, valid, gross, sig_d, ent_d, ext_d) -> pd.DataFrame:
    """valid: the start can be priced and every feature the rule reads exists. Triggered additionally needs the conditions and a non-zero direction."""
    for c in rule["conditions"]:
        valid = valid & ~np.isnan(F[c["feature"]])
    for v in rule["direction"].values():
        if isinstance(v, str):
            valid = valid & ~np.isnan(F[v])
    ok = np.ones(n, bool)
    for c in rule["conditions"]:
        ok &= _cond(np.nan_to_num(F[c["feature"]], nan=0.0), c["op"], c["value"])
    dr = np.nan_to_num(_direction(rule, F, n), nan=0.0)
    trig = valid & ok & (dr != 0)
    out = pd.DataFrame({"signal_date": sig_d, "entry_date": ent_d, "exit_date": ext_d, "triggered": trig, "direction": np.where(trig, dr, 0.0), "gross": gross})
    return out[valid].reset_index(drop=True)


# ----------------------------------------------------------------------------------------------- scanners
def scan_daily(rule: dict, daily: pd.DataFrame, vix: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per start day i whose trade can be priced: signal_date, entry_date, exit_date, triggered, direction, gross (LONG return exit/entry-1)."""
    d = daily.sort_values("date").reset_index(drop=True)
    n = len(d)
    O, C, dts = d["open"].values.astype(float), d["close"].values.astype(float), d["date"].values.astype("datetime64[D]")
    V = np.full(n, np.nan)
    if vix is not None and len(vix):
        V = d[["date"]].merge(vix[["date", "close"]].drop_duplicates("date"), on="date", how="left")["close"].values.astype(float)
    F: dict = {}
    for name in {c["feature"] for c in rule["conditions"]} | {v for v in rule["direction"].values() if isinstance(v, str)}:
        a = np.full(n, np.nan)
        m = FEAT_RE.match(name)
        if m and m.group(1) == "ret":
            k = int(m.group(2))
            a[k:] = C[k:] / C[:-k] - 1
        elif m:
            k = int(m.group(2))
            a[k:] = V[k:] / V[:-k] - 1
        elif name == "vix_level":
            a = V.copy()
        elif name == "gap_next":
            a[:-1] = O[1:] / C[:-1] - 1
        elif name == "weekday":
            a = pd.DatetimeIndex(d["date"]).weekday.values.astype(float)
        F[name] = a
    ke, kx = rule["entry"]["day"], rule["exit"]["day"]
    Pe, Px = (O if rule["entry"]["px"] == "open" else C), (O if rule["exit"]["px"] == "open" else C)
    i = np.arange(n)
    valid = i + kx < n
    ie, ix = np.minimum(i + ke, n - 1), np.minimum(i + kx, n - 1)
    gross = Px[ix] / Pe[ie] - 1
    return _finish(rule, F, n, valid, gross, dts, dts[ie], dts[ix])


def scan_intraday(rule: dict, m5: pd.DataFrame) -> pd.DataFrame:
    s = rule["signal"]
    pts = [s["from"], s["to"], rule["entry"], rule["exit"]]
    times = tuple(sorted({p[2:] for p in pts}))
    b = fi.bars_by_day(m5, times)
    n = len(b)

    def px(p):
        return b[("o_" if p[0] == "o" else "c_") + p[2:]].values.astype(float)
    F = {"sig_ret": px(s["to"]) / px(s["from"]) - 1, "weekday": pd.DatetimeIndex(b.index).weekday.values.astype(float)}
    gross = px(rule["exit"]) / px(rule["entry"]) - 1
    valid = ~(np.isnan(px(s["from"])) | np.isnan(px(s["to"])) | np.isnan(px(rule["entry"])) | np.isnan(px(rule["exit"])))
    days = b.index.values.astype("datetime64[D]")
    return _finish(rule, F, n, valid, gross, days, days, days)


def scan(rule: dict, daily=None, vix=None, m5=None) -> pd.DataFrame:
    validate_rule(rule)
    if rule["kind"] == "daily":
        if daily is None:
            raise RuleError("daily rule needs daily data")
        if needs(rule)["vix"] and (vix is None or not len(vix)):
            raise RuleError("this rule reads India VIX but no VIX data was given")
        return scan_daily(rule, daily, vix)
    if m5 is None:
        raise RuleError("intraday rule needs 5-minute data")
    return scan_intraday(rule, m5)


# ----------------------------------------------------------------------------------------------- to the Task 5 Trades object
def to_trades(idea_no: int, name: str, sc: pd.DataFrame) -> "fi.Trades":
    """Build the Task 5 Trades object so the SAME statistics (bootstrap, random-entry null, halves) run on it.
    The null draws random starts from every priceable start of the same template (key 1)."""
    t = sc[sc["triggered"]]
    win = (sc["signal_date"].iloc[0], sc["signal_date"].iloc[-1]) if len(sc) else (date(1970, 1, 1), date(1970, 1, 1))
    win = tuple(pd.Timestamp(x).date() for x in win)
    return fi._trades(idea_no, name, t["entry_date"].values, t["direction"].values, t["gross"].values, np.ones(len(t), int),
                      {1: sc["gross"].values.astype(float)}, win)
