"""Regression metrics and generic timed train/predict helper."""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

TModel = TypeVar("TModel")


def mae_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    return mae, rmse


def benchmark_model(
    train_fn: Callable[..., TModel],
    predict_fn: Callable[[TModel, Any], np.ndarray],
    X_train: Any,
    y_train: np.ndarray,
    X_test: Any,
    y_test: np.ndarray,
) -> dict[str, float]:
    """
    Standard timed benchmark: fit ``train_fn(X_train, y_train)``, predict on ``X_test``.

    Returns MAE, RMSE, train_time, infer_time (seconds).
    """
    t0 = time.perf_counter()
    model = train_fn(X_train, y_train)
    train_time = time.perf_counter() - t0

    t1 = time.perf_counter()
    y_pred = predict_fn(model, X_test)
    infer_time = time.perf_counter() - t1

    mae, rmse = mae_rmse(np.asarray(y_test).ravel(), np.asarray(y_pred).ravel())
    return {
        "MAE": mae,
        "RMSE": rmse,
        "train_time": train_time,
        "infer_time": infer_time,
    }
