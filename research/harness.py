"""FROZEN evaluation harness. The research agent must not edit this file.

Target: log(high/low) of the NEXT bar (a range/volatility proxy), forecast from bars <= t.
Why not direction: next-bar direction is ~a coin flip; range is persistent and forecastable,
and it feeds sizing/options. Guardrails: walk-forward origins, naive baselines, a
trial-count-adjusted significance bar, and a minimum effect size.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

LEDGER = Path(__file__).parent / "ledger.jsonl"
QUANTILES = (0.1, 0.5, 0.9)
MIN_TRAIN = 250
MIN_REL_IMPROVEMENT = 0.02  # must beat the best baseline by >= 2% relative MAE ...
ALPHA = 0.05  # ... and the bootstrap lower bound must clear this level / n_trials
BLOCK = 5

Predictor = Callable[[pd.DataFrame], dict]  # history -> {"mean": float, "q": {0.1:..,0.5:..,0.9:..}?}


def log_range(df: pd.DataFrame) -> pd.Series:
    return np.log(df["high"] / df["low"])


# ---- baselines (analogues of random walk / drift) -------------------------------------
def _emp_q(x: np.ndarray) -> dict:
    return {q: float(np.quantile(x, q)) for q in QUANTILES}


def baseline_last(h: pd.DataFrame) -> dict:  # random walk: tomorrow = today
    r = log_range(h).to_numpy()
    return {"mean": r[-1], "q": _emp_q(r[-60:])}


def baseline_mean20(h: pd.DataFrame) -> dict:  # "drift": trailing average
    r = log_range(h).to_numpy()
    return {"mean": r[-20:].mean(), "q": _emp_q(r[-60:])}


def baseline_ewma(h: pd.DataFrame, lam: float = 0.94) -> dict:
    r = log_range(h).to_numpy()[-120:]
    w = lam ** np.arange(len(r))[::-1]
    return {"mean": float((w * r).sum() / w.sum()), "q": _emp_q(r[-60:])}


BASELINES: dict[str, Predictor] = {
    "random_walk": baseline_last,
    "mean20": baseline_mean20,
    "ewma94": baseline_ewma,
}


# ---- walk-forward ---------------------------------------------------------------------
def walk_forward(df: pd.DataFrame, predict: Predictor, step: int = 1) -> pd.DataFrame:
    """One forecast per origin i using ONLY df.iloc[:i+1]; actual is bar i+1."""
    y = log_range(df).to_numpy()
    out = []
    for i in range(MIN_TRAIN, len(df) - 1, step):
        p = predict(df.iloc[: i + 1].copy())
        row = {"date": df["date"].iloc[i + 1], "y": y[i + 1], "mean": float(p["mean"])}
        for q in QUANTILES:
            row[f"q{q}"] = float(p["q"][q]) if p.get("q") else np.nan
        out.append(row)
    return pd.DataFrame(out)


def mae(f: pd.DataFrame) -> np.ndarray:
    return np.abs(f["y"] - f["mean"]).to_numpy()


def pinball(f: pd.DataFrame) -> float:
    if f[[f"q{q}" for q in QUANTILES]].isna().any().any():
        return float("nan")
    tot = 0.0
    for q in QUANTILES:
        e = f["y"] - f[f"q{q}"]
        tot += np.maximum(q * e, (q - 1) * e).mean()
    return float(tot / len(QUANTILES))


def block_bootstrap_lower(d: np.ndarray, alpha: float, n_boot: int = 20000, seed: int = 0) -> float:
    """alpha-quantile of the block-bootstrapped mean of d (paired loss improvement)."""
    rng = np.random.default_rng(seed)
    n = len(d)
    n_blocks = -(-n // BLOCK)
    starts = rng.integers(0, n - BLOCK + 1, size=(n_boot, n_blocks))
    idx = (starts[:, :, None] + np.arange(BLOCK)).reshape(n_boot, -1)[:, :n]
    return float(np.quantile(d[idx].mean(axis=1), alpha))


# ---- trial ledger (multiple-comparison control) ---------------------------------------
def seen_hashes() -> set:
    if not LEDGER.exists():
        return set()
    return {json.loads(l)["code_hash"] for l in LEDGER.read_text().splitlines() if l}


def log_trial(code_hash: str, summary: dict) -> None:
    with LEDGER.open("a") as fh:
        fh.write(json.dumps({"t": time.time(), "code_hash": code_hash, **summary}) + "\n")


def code_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def evaluate(df: pd.DataFrame, predict: Predictor, trials: int, step: int = 1) -> dict:
    cand = walk_forward(df, predict, step)
    base = {k: walk_forward(df, fn, step) for k, fn in BASELINES.items()}
    cand_mae = mae(cand)
    best_name = min(base, key=lambda k: mae(base[k]).mean())
    best_mae = mae(base[best_name])
    d = best_mae - cand_mae  # >0 means candidate better
    rel = float(d.mean() / best_mae.mean())
    alpha_adj = ALPHA / max(trials, 1)  # Bonferroni across every distinct candidate tried
    lower = block_bootstrap_lower(d, alpha_adj)
    return {
        "n_origins": len(cand),
        "mae": {"candidate": float(cand_mae.mean()), **{k: float(mae(v).mean()) for k, v in base.items()}},
        "pinball": {"candidate": pinball(cand), **{k: pinball(v) for k, v in base.items()}},
        "best_baseline": best_name,
        "rel_improvement": rel,
        "n_trials": trials,
        "alpha_adj": alpha_adj,
        "ci_lower_gain": lower,
        "verdict": "PASS" if (rel >= MIN_REL_IMPROVEMENT and lower > 0) else "FAIL",
    }
