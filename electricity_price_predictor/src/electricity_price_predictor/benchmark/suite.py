"""Orchestrated benchmark: naive, GAM+AR(1), LightGBM, LSTM on one tabular frame and split."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd

from .data_prep import TabularModelFrame, prepare_tabular_model_frame, time_series_split_ends
from .gam_ar1 import GamAr1AdditiveModel
from .lightgbm_model import train_lightgbm_benchmark
from .lstm_model import predict_lstm, train_lstm_benchmark
from .metrics import mae_rmse


def run_benchmark_suite(
    df: pd.DataFrame,
    *,
    target_col: str = "day_ahead_price",
    train_frac: float = 0.7,
    valid_frac: float = 0.85,
    lstm_seq_len: int = 24,
    lstm_epochs: int = 50,
    lstm_hidden: int = 64,
    lstm_dropout: float = 0.2,
    naive_lag_col: str = "lagged_price_24",
    include_lstm: bool = True,
    float_dtype: str | None = "float32",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Run all baselines on the same chronological split.

    Returns ``(results_df, bundle)`` where ``bundle`` holds intermediate objects for plotting.
    """
    prep = prepare_tabular_model_frame(df, target_col=target_col, float_dtype=float_dtype)
    dm = prep.df_model
    n = len(dm)
    train_end, valid_end = time_series_split_ends(n, train_frac=train_frac, valid_frac=valid_frac)

    y_valid = dm[target_col].iloc[train_end:valid_end].values
    y_test = dm[target_col].iloc[valid_end:].values

    rows: list[dict[str, Any]] = []
    bundle: dict[str, Any] = {"prep": prep, "train_end": train_end, "valid_end": valid_end}

    # --- Naive (lag-24 persistence)
    if naive_lag_col not in dm.columns:
        raise KeyError(f"Naive benchmark requires column {naive_lag_col!r} on the feature frame.")
    t_infer0 = time.perf_counter()
    naive_valid = dm[naive_lag_col].iloc[train_end:valid_end].to_numpy()
    naive_test = dm[naive_lag_col].iloc[valid_end:].to_numpy()
    infer_naive = time.perf_counter() - t_infer0
    mae_v, rmse_v = mae_rmse(y_valid, naive_valid)
    mae_t, rmse_t = mae_rmse(y_test, naive_test)
    rows.append(
        {
            "model": "naive_lag24",
            "split": "valid",
            "MAE": mae_v,
            "RMSE": rmse_v,
            "train_time": 0.0,
            "infer_time": infer_naive * 0.5,
        }
    )
    rows.append(
        {
            "model": "naive_lag24",
            "split": "test",
            "MAE": mae_t,
            "RMSE": rmse_t,
            "train_time": 0.0,
            "infer_time": infer_naive * 0.5,
        }
    )

    # --- GAM + AR(1)
    gam_model = GamAr1AdditiveModel()
    t0 = time.perf_counter()
    gam_model.fit(dm, train_end=train_end, valid_end=valid_end)
    train_gam = time.perf_counter() - t0
    t1 = time.perf_counter()
    gam_series = gam_model.predict_additive()
    infer_gam = time.perf_counter() - t1
    bundle["gam_ar1"] = gam_model
    bundle["gam_ar1_series"] = gam_series

    g_valid = gam_series.reindex(dm.index).iloc[train_end:valid_end].values
    g_test = gam_series.reindex(dm.index).iloc[valid_end:].values
    mae_v, rmse_v = mae_rmse(y_valid, g_valid)
    mae_t, rmse_t = mae_rmse(y_test, g_test)
    rows.append(
        {
            "model": "gam_ar1",
            "split": "valid",
            "MAE": mae_v,
            "RMSE": rmse_v,
            "train_time": train_gam,
            "infer_time": infer_gam,
        }
    )
    rows.append(
        {
            "model": "gam_ar1",
            "split": "test",
            "MAE": mae_t,
            "RMSE": rmse_t,
            "train_time": train_gam,
            "infer_time": infer_gam,
        }
    )

    # --- LightGBM
    t0 = time.perf_counter()
    lgb_res = train_lightgbm_benchmark(prep, train_end, valid_end)
    train_lgb = time.perf_counter() - t0
    t1 = time.perf_counter()
    _ = lgb_res.model.predict(lgb_res.X_valid)
    _ = lgb_res.model.predict(lgb_res.X_test)
    infer_lgb = time.perf_counter() - t1
    bundle["lightgbm"] = lgb_res

    mae_v, rmse_v = mae_rmse(lgb_res.y_valid.values, lgb_res.valid_pred)
    mae_t, rmse_t = mae_rmse(lgb_res.y_test.values, lgb_res.test_pred)
    rows.append(
        {
            "model": "lightgbm",
            "split": "valid",
            "MAE": mae_v,
            "RMSE": rmse_v,
            "train_time": train_lgb,
            "infer_time": infer_lgb / 2,
        }
    )
    rows.append(
        {
            "model": "lightgbm",
            "split": "test",
            "MAE": mae_t,
            "RMSE": rmse_t,
            "train_time": train_lgb,
            "infer_time": infer_lgb / 2,
        }
    )

    # --- LSTM
    if include_lstm:
        art, timing, X_seq, y_seq, va_ix, te_ix = train_lstm_benchmark(
            prep,
            train_end,
            valid_end,
            seq_len=lstm_seq_len,
            hidden_size=lstm_hidden,
            dropout=lstm_dropout,
            epochs=lstm_epochs,
        )
        bundle["lstm"] = art

        t_inf = time.perf_counter()
        pred_va = predict_lstm(art, X_seq[va_ix])
        pred_te = predict_lstm(art, X_seq[te_ix])
        infer_lstm = time.perf_counter() - t_inf

        mae_v, rmse_v = mae_rmse(y_seq[va_ix], pred_va)
        mae_t, rmse_t = mae_rmse(y_seq[te_ix], pred_te)
        rows.append(
            {
                "model": "lstm",
                "split": "valid",
                "MAE": mae_v,
                "RMSE": rmse_v,
                "train_time": timing["train_time"],
                "infer_time": infer_lstm / 2,
            }
        )
        rows.append(
            {
                "model": "lstm",
                "split": "test",
                "MAE": mae_t,
                "RMSE": rmse_t,
                "train_time": timing["train_time"],
                "infer_time": infer_lstm / 2,
            }
        )

    return pd.DataFrame(rows), bundle
