"""THE FILE THE AGENT EDITS (together with ENGINE exits below). Everything else in scalp/ is frozen.

on_bar(o, h, l, c) receives numpy arrays of TODAY's bars up to and including the latest closed
bar and returns +1 (go long), -1 (go short) or 0. Only called when flat. Use only these arrays.
Default: momentum burst - enter in the direction of a move that is large relative to recent noise.
"""

import numpy as np

VOL_WINDOW = 20  # bars used to estimate recent noise (keep equal to the engine's sigma_window)
PARAMS = dict(lookback=6, z_entry=1.5)
ENGINE = dict(stop_k=1.5, target_k=2.0, max_hold=12)  # futures exits, in units of recent bar volatility
OPTIONS = dict(stop_pct=0.20, target_pct=0.30, max_hold=8)  # option-buying exits, in % of premium


class Momentum:
    def __init__(self, lookback, z_entry):
        self.L, self.z = lookback, z_entry

    def on_bar(self, o, h, l, c):
        if len(c) < self.L + VOL_WINDOW + 1:
            return 0
        sig = np.std(np.diff(c[-(VOL_WINDOW + 1):]))
        if sig <= 0:
            return 0
        z = (c[-1] - c[-1 - self.L]) / (sig * np.sqrt(self.L))
        return 1 if z > self.z else (-1 if z < -self.z else 0)


def make():
    return Momentum(**PARAMS)
