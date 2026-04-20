"""Shared tabular preprocessing for benchmark models (matches notebook conventions)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TabularModelFrame:
    """Numeric feature matrix + target after coercion, sorted by time index."""

    df_model: pd.DataFrame
    feature_cols: list[str]
    target_col: str


def prepare_tabular_model_frame(
    df: pd.DataFrame,
    target_col: str = "day_ahead_price",
    *,
    float_dtype: str | None = "float32",
) -> TabularModelFrame:
    """
    Drop non-feature columns, coerce to numeric, drop NaNs (same as notebook LightGBM path).

    If ``float_dtype`` is set (default ``float32``), cast numeric columns for lower memory.
    """
    feature_cols = [c for c in df.columns if c != target_col]
    df_model = df[feature_cols + [target_col]].copy()
    df_model[feature_cols + [target_col]] = df_model[feature_cols + [target_col]].apply(
        pd.to_numeric, errors="coerce"
    )
    df_model = df_model.dropna()
    if df_model.empty:
        raise ValueError("No rows left after numeric coercion and NaN removal.")

    df_model = df_model.sort_index()
    if float_dtype:
        df_model[feature_cols + [target_col]] = df_model[feature_cols + [target_col]].astype(
            float_dtype
        )

    non_numeric = df_model[feature_cols].select_dtypes(exclude=[np.number, "bool"]).columns.tolist()
    if non_numeric:
        raise ValueError(f"Non-numeric columns after coercion: {non_numeric}")

    return TabularModelFrame(df_model=df_model, feature_cols=feature_cols, target_col=target_col)


def time_series_split_ends(
    n: int, train_frac: float = 0.7, valid_frac: float = 0.85
) -> tuple[int, int]:
    """Return ``(train_end, valid_end)`` index boundaries (iloc semantics, exclusive end for train)."""
    train_end = int(n * train_frac)
    valid_end = int(n * valid_frac)
    if not (0 < train_end < valid_end < n):
        raise ValueError(f"Invalid split for n={n}: train_end={train_end}, valid_end={valid_end}")
    return train_end, valid_end
