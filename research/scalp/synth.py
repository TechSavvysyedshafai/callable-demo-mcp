"""Fake intraday bars for dry runs. phi>0 plants momentum (a real, exploitable edge) to prove the
pipeline can detect one; phi=0 is a pure random walk (the pipeline must NOT find anything)."""

import numpy as np
import pandas as pd


def synthetic_intraday(n_days=120, minutes=5, phi=0.0, bar_vol=0.0006, seed=0, start="2024-01-01"):
    rng = np.random.default_rng(seed)
    per_day = 375 // minutes
    rows, price, logv = [], 24000.0, 0.0
    for d in pd.bdate_range(start, periods=n_days):
        logv = 0.8 * logv + 0.3 * rng.standard_normal()
        sig, r_prev = bar_vol * np.exp(0.5 * logv), 0.0
        for k in range(per_day):
            r = phi * r_prev + sig * rng.standard_normal()
            r_prev = r
            o, c = price, price * np.exp(r)
            wick = abs(rng.standard_normal()) * sig * price * 0.4
            rows.append([d + pd.Timedelta(hours=9, minutes=15 + k * minutes), o,
                         max(o, c) + wick, min(o, c) - wick, c, 1000])
            price = c
    return pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
