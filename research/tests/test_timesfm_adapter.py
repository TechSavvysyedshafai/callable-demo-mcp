"""Plumbing test with a stand-in `timesfm3` (the real weights are not needed to check shapes)."""

import sys
import types
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
import kite_data as kd  # noqa: E402


class FakeEvaluator:
    def __init__(self, cfg): ...

    def predict_batch(self, contexts, horizon, return_quantiles, use_symmetric_averaging, **kw):
        for c in contexts:
            c = np.asarray(c)
            n_var = 1 if c.ndim == 1 else c.shape[0]
            last = c.reshape(n_var, -1)[:, -1]
            fc = np.tile(last[:, None], (1, horizon))
            q = fc[..., None] + np.linspace(-0.2, 0.2, 9)
            if c.ndim == 1:
                fc, q = fc[0], q[0]
            yield SimpleNamespace(forecast=fc, quantiles=q)


def test_both_modes():
    sys.modules["timesfm3"] = types.SimpleNamespace(TimesFM3Evaluator=FakeEvaluator, ModelConfig=lambda **k: k)
    sys.modules["torch"] = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
    import candidate_timesfm as c

    df = kd.synthetic(n=600)
    for cov in (False, True):
        c.USE_COVARIATES = cov
        p = c.predict(df)
        last = float(np.log(df["high"].iloc[-1] / df["low"].iloc[-1]))
        assert abs(p["mean"] - last) < 1e-5
        assert p["q"][0.1] < p["q"][0.5] < p["q"][0.9]
    print("ok")


if __name__ == "__main__":
    test_both_modes()
