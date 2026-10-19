"""Independent recomputation of B5-01 from the RAW CSV files with the standard `csv` module only (no pandas, no numpy, no crowd_core, no wheel/selling code).
It re-derives: the trading-day list, the entry day (later of expiry-7d rule and first day after the previous expiry), the 09:25 spot, the 09:30 open, the strike
window, PCR, x, z (expanding, last 52, sample sd), the trades, net returns and rupees, and compares them with research/crowd/results/crowd_weeks.csv and
crowd_trades.csv written by crowd_run.py.   python research/crowd/crowd_crosscheck.py
Writes results/crowd_crosscheck.txt."""

import csv
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OPT = DATA / "expired_options" / "NIFTY"
OUT = HERE / "results"
FIRST, LAST = date(2024, 10, 3), date(2026, 4, 16)


def rows(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    # --- index bars: {datetime: (open, close)}
    bars = {}
    for r in rows(DATA / "nifty_5minute_dev.csv"):
        bars[datetime.strptime(r["date"], "%Y-%m-%d %H:%M:%S")] = (float(r["open"]), float(r["close"]))
    days = sorted({t.date() for t in bars})
    close_day = {datetime.strptime(r["date"][:10], "%Y-%m-%d").date(): float(r["close"]) for r in rows(DATA / "nifty_day_dev.csv")}
    exps = sorted(d for d in (datetime.strptime(r["expiry"], "%Y-%m-%d").date() for r in rows(DATA / "nifty_expiries.csv")) if FIRST <= d <= LAST)

    def oi_at(ex, k, kind, ts):
        f = OPT / f"{ex.isoformat()}_{k}{kind}.csv"
        if not f.exists():
            return None
        want = ts.strftime("%Y-%m-%d %H:%M:%S")
        with open(f, newline="") as fh:
            for line in csv.DictReader(fh):
                if line["date"] == want:
                    v = line["oi"].strip()
                    return None if v == "" or v.lower() == "nan" else float(v)
        return None

    hist, weeks, trades = [], [], []
    for k, ex in enumerate(exps):
        # entry day: later of (nearest trading day on or before ex-7) and (first trading day strictly after the previous expiry)
        a = max([d for d in days if d <= ex - timedelta(days=7)], default=None)
        b = min([d for d in days if d > exps[k - 1]], default=None) if k > 0 else None
        d0 = a if k == 0 or b is None else (max(a, b) if a is not None else b)
        w = {"k": k, "expiry": ex, "entry_day": d0, "n": 0, "x": None, "z": None, "dir": 0, "skip": ""}
        sig_t, ent_t = (datetime(d0.year, d0.month, d0.day, 9, 25), datetime(d0.year, d0.month, d0.day, 9, 30)) if d0 else (None, None)
        if d0 is None:
            w["skip"] = "no_entry_day"
        elif sig_t not in bars:
            w["skip"] = "no_0925_bar"
        elif ent_t not in bars:
            w["skip"] = "no_0930_bar"
        else:
            S = bars[sig_t][1]
            R = int(math.floor(S / 50 + 0.5)) * 50
            co = po = 0.0
            for K in range(R - 250, R + 251, 50):
                if abs(K - S) > 250:
                    continue
                c, p = oi_at(ex, K, "CE", sig_t), oi_at(ex, K, "PE", sig_t)
                if c is None or p is None:
                    continue
                w["n"] += 1
                co += c
                po += p
            if w["n"] == 0:
                w["skip"] = "no_oi_at_signal"
            elif co <= 0 or po <= 0:
                w["skip"] = "zero_oi_side"
            else:
                w["x"] = math.log(po / co)
                prior = hist[-52:]
                if len(prior) < 20:
                    w["skip"] = "lt20_history"
                else:
                    m = sum(prior) / len(prior)
                    sd = math.sqrt(sum((v - m) ** 2 for v in prior) / (len(prior) - 1))
                    if sd == 0:
                        w["skip"] = "zero_sd"
                    else:
                        w["z"] = (w["x"] - m) / sd
                        if w["z"] <= -1.0 + 1e-12:
                            w["dir"] = -1
                        elif w["z"] >= 1.0 - 1e-12:
                            w["dir"] = 1
                hist.append(w["x"])
            if w["dir"] != 0:
                e, x_ = bars[ent_t][0], close_day[ex]
                trades.append({"expiry": ex, "dir": w["dir"], "entry": e, "exit": x_, "net": w["dir"] * (x_ / e - 1) - 0.001,
                               "rs": w["dir"] * (x_ - e) * 75 - 0.001 * e * 75})
        weeks.append(w)

    # --- compare with the engine's files
    eng_w = rows(OUT / "crowd_weeks.csv")
    eng_t = rows(OUT / "crowd_trades.csv")
    bad = 0
    lines = []
    if len(eng_w) != len(weeks):
        bad += 1
        lines.append(f"week count differs: engine {len(eng_w)} vs crosscheck {len(weeks)}")
    maxdx = maxdz = 0.0
    for e, w in zip(eng_w, weeks):
        ex_ok = e["expiry"] == w["expiry"].isoformat() and e["entry_day"] == (w["entry_day"].isoformat() if w["entry_day"] else "None")
        dir_ok = int(float(e["direction"])) == w["dir"]
        n_ok = int(float(e["n_strikes"])) == w["n"] if w["skip"] not in ("no_entry_day", "no_0925_bar", "no_0930_bar") else True
        x_ok = (e["x"] == "") == (w["x"] is None)
        z_ok = (e["z"] == "") == (w["z"] is None)
        if w["x"] is not None and e["x"] != "":
            maxdx = max(maxdx, abs(float(e["x"]) - w["x"]))
        if w["z"] is not None and e["z"] != "":
            maxdz = max(maxdz, abs(float(e["z"]) - w["z"]))
        if not (ex_ok and dir_ok and n_ok and x_ok and z_ok) or e["skipped"] != w["skip"]:
            bad += 1
            lines.append(f"week {w['expiry']}: engine {e} vs crosscheck {w}")
    if len(eng_t) != len(trades):
        bad += 1
        lines.append(f"trade count differs: engine {len(eng_t)} vs crosscheck {len(trades)}")
    maxdn = maxdr = 0.0
    for e, t in zip(eng_t, trades):
        if e["expiry"] != t["expiry"].isoformat() or int(float(e["direction"])) != t["dir"]:
            bad += 1
            lines.append(f"trade mismatch {e} vs {t}")
            continue
        maxdn = max(maxdn, abs(float(e["net_ret"]) - t["net"]))
        maxdr = max(maxdr, abs(float(e["net_rs"]) - t["rs"]))
    n = len(trades)
    mean_net = sum(t["net"] for t in trades) / n if n else float("nan")
    mean_gross = sum(t["dir"] * (t["exit"] / t["entry"] - 1) for t in trades) / n if n else float("nan")
    ok = bad == 0 and maxdx < 1e-9 and maxdz < 1e-9 and maxdn < 1e-12 and maxdr < 1e-6
    lines += [f"weeks compared: {len(weeks)}; trades: engine {len(eng_t)} / crosscheck {n}",
              f"max |x diff| {maxdx:.3e}; max |z diff| {maxdz:.3e}; max |net return diff| {maxdn:.3e}; max |net rupee diff| {maxdr:.3e}",
              f"crosscheck mean net per trade {mean_net * 100:+.5f}%; mean at zero cost {mean_gross * 100:+.5f}%; long {sum(t['dir'] > 0 for t in trades)}, short {sum(t['dir'] < 0 for t in trades)}",
              "CROSSCHECK " + ("OK: identical" if ok else "MISMATCH")]
    OUT.mkdir(exist_ok=True)
    (OUT / "crowd_crosscheck.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
