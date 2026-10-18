"""Underlying configs + expiry rules. EVERY NUMBER HERE IS FROM MEMORY AND CHANGES (lot sizes, which index
has weeklies, expiry weekday, holidays). Verify against NSE/BSE circulars. The live code reads real lot
sizes and expiries from Kite's instruments dump; these are used only by the model-based backtest."""

from datetime import date, datetime, time, timedelta

UNDERLYINGS = {
    # lot: contract size; step: strike spacing; weekly: weekly expiries exist; wd: expiry weekday (Mon=0)
    "NIFTY":      dict(lot=75, step=50,  weekly=True,  wd=1, exch="NFO", index_symbol="NIFTY 50",           token=256265),
    "BANKNIFTY":  dict(lot=30, step=100, weekly=False, wd=1, exch="NFO", index_symbol="NIFTY BANK",         token=260105),
    "FINNIFTY":   dict(lot=65, step=50,  weekly=False, wd=1, exch="NFO", index_symbol="NIFTY FIN SERVICE",  token=257801),
    "MIDCPNIFTY": dict(lot=140, step=25, weekly=False, wd=1, exch="NFO", index_symbol="NIFTY MID SELECT",   token=288009),
    "SENSEX":     dict(lot=20, step=100, weekly=True,  wd=3, exch="BFO", index_symbol="SENSEX",             token=265),
}
EXPIRY_TIME = time(15, 30)


def _on_or_after(d: date, wd: int) -> date:
    return d + timedelta(days=(wd - d.weekday()) % 7)


def _last_weekday_of_month(y: int, m: int, wd: int) -> date:
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    d = nxt - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - wd) % 7)


def next_expiry(cfg: dict, d: date) -> date:
    """First expiry on or after d. Uses the REAL expiry calendar (cfg["calendar"], sorted dates from Upstox) when
    given and covering d; otherwise a formula (weekly if the underlying has weeklies, else monthly)."""
    cal = cfg.get("calendar")
    if cal and cal[0] <= d <= cal[-1]:
        return next(e for e in cal if e >= d)
    if cfg["weekly"]:
        return _on_or_after(d, cfg["wd"])
    e = _last_weekday_of_month(d.year, d.month, cfg["wd"])
    return e if e >= d else _last_weekday_of_month(d.year + (d.month == 12), d.month % 12 + 1, cfg["wd"])


def years_to_expiry(expiry: date, ts: datetime) -> float:
    secs = (datetime.combine(expiry, EXPIRY_TIME) - ts).total_seconds()
    return max(secs, 60.0) / (365.0 * 86400.0)
