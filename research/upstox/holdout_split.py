"""Keep side data (VIX, expiry calendar) from leaking the hidden holdout period into the dev folder."""

from __future__ import annotations

import pandas as pd


def split_vix(v: pd.DataFrame, cut: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(dev rows with date <= cut, holdout rows with date > cut)."""
    return v[v["date"] <= cut].reset_index(drop=True), v[v["date"] > cut].reset_index(drop=True)


def dev_expiries(expiries: list[str], cut: pd.Timestamp) -> list[str]:
    """Expiries up to the cut plus the FIRST one after it (needed to price the last dev sessions); later ones are dropped."""
    ex = sorted(expiries)
    keep = [e for e in ex if pd.Timestamp(e) <= cut]
    after = [e for e in ex if pd.Timestamp(e) > cut]
    return keep + after[:1]
