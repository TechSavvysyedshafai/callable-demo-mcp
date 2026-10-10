"""THE FILE THE AGENT EDITS. Everything else in research/ is frozen.

predict(history) gets bars up to and including the forecast origin (columns: date, open,
high, low, close, volume) and returns the forecast of log(high/low) for the NEXT bar:
    {"mean": float, "q": {0.1: float, 0.5: float, 0.9: float}}   # "q" optional
Baseline here: a HAR-style blend of 1/5/22-bar average log-ranges. Replace with anything
(TimesFM adapter, GARCH, gradient boosting) - but only use `history`, never read other files.
"""

import numpy as np


def predict(history):
    r = np.log(history["high"] / history["low"]).to_numpy()
    mean = 0.4 * r[-1] + 0.3 * r[-5:].mean() + 0.3 * r[-22:].mean()
    resid = r[-60:] - r[-60:].mean()
    return {"mean": float(mean), "q": {q: float(mean + np.quantile(resid, q)) for q in (0.1, 0.5, 0.9)}}
