"""TimesFM-3 candidate. To use it:  cp candidate_timesfm.py candidate.py && python evaluate.py

Zero-shot forecast of next-bar log(high/low). Needs the `timesfm3` package (install from
github.com/google-research/timesfm: `pip install -e .[torch]`) and the weights
`google/timesfm-3.0-pytorch` from Hugging Face.

LICENSE: the 3.0 weights are non-commercial / non-production (TimesFM Non-Commercial License v1.0).
Research on your own is fine; using forecasts to run a trading business is not covered. Check it.
"""

import numpy as np

CHECKPOINT = "google/timesfm-3.0-pytorch"
CONTEXT = 512  # bars of history given to the model
USE_COVARIATES = False  # True: also pass |return| and volume as past-only covariates
Q_IDX = {0.1: 0, 0.5: 4, 0.9: 8}  # the model returns 9 quantiles, 0.1 .. 0.9

_model = None


def _load():
    global _model
    if _model is None:
        import torch
        from timesfm3 import ModelConfig, TimesFM3Evaluator

        _model = TimesFM3Evaluator(
            ModelConfig(
                checkpoint_path=CHECKPOINT,
                per_core_batch_size=1,
                device="cuda" if torch.cuda.is_available() else "cpu",
            )
        )
    return _model


def predict(history):
    h = history.tail(CONTEXT + 1)
    y = np.log(h["high"] / h["low"]).to_numpy(dtype=np.float32)
    kwargs = {}
    if USE_COVARIATES:
        ret = np.abs(np.diff(np.log(h["close"].to_numpy()), prepend=np.nan))
        ret = np.nan_to_num(ret).astype(np.float32)
        vol = np.log1p(h["volume"].to_numpy(dtype=np.float64)).astype(np.float32)
        contexts = [y[None, :]]
        kwargs["past_only_covariates"] = [np.stack([ret, vol])]
    else:
        contexts = [y]

    out = next(
        iter(
            _load().predict_batch(
                contexts=contexts,
                horizon=1,
                return_quantiles=True,
                use_symmetric_averaging=False,
                **kwargs,
            )
        )
    )
    mean = float(np.asarray(out.forecast).reshape(-1)[0])
    q = np.asarray(out.quantiles).reshape(-1, 9)[0]
    return {"mean": mean, "q": {k: float(q[i]) for k, i in Q_IDX.items()}}
