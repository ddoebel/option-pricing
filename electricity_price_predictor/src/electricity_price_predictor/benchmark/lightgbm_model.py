"""LightGBM regressor training (defaults aligned with analyze_data notebook)."""

from __future__ import annotations

from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .data_prep import TabularModelFrame


@dataclass
class LightGBMBenchmarkResult:
    model: lgb.LGBMRegressor
    feature_cols: list[str]
    target_col: str
    train_end: int
    valid_end: int
    X_train: pd.DataFrame
    X_valid: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_valid: pd.Series
    y_test: pd.Series
    valid_pred: np.ndarray
    test_pred: np.ndarray


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def train_lightgbm_benchmark(
    prep: TabularModelFrame,
    train_end: int,
    valid_end: int,
    *,
    n_estimators: int = 2000,
    learning_rate: float = 0.03,
    num_leaves: int = 31,
    max_depth: int = 6,
    min_child_samples: int = 30,
    subsample: float = 0.8,
    colsample_bytree: float = 0.8,
    reg_alpha: float = 0.1,
    reg_lambda: float = 0.1,
    random_state: int = 42,
    early_stopping_rounds: int = 100,
    verbosity: int = -1,
) -> LightGBMBenchmarkResult:
    """Time-ordered train / valid / test split and fit with early stopping on validation L1."""
    df_model = prep.df_model
    feature_cols = prep.feature_cols
    target_col = prep.target_col

    train = df_model.iloc[:train_end]
    valid = df_model.iloc[train_end:valid_end]
    test = df_model.iloc[valid_end:]

    X_train, y_train = train[feature_cols], train[target_col]
    X_valid, y_valid = valid[feature_cols], valid[target_col]
    X_test, y_test = test[feature_cols], test[target_col]

    model = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        num_leaves=num_leaves,
        max_depth=max_depth,
        min_child_samples=min_child_samples,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        reg_alpha=reg_alpha,
        reg_lambda=reg_lambda,
        random_state=random_state,
        verbosity=verbosity,
    )
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_valid, y_valid)],
        eval_metric="l1",
        callbacks=[lgb.early_stopping(early_stopping_rounds)],
    )
    valid_pred = model.predict(X_valid)
    test_pred = model.predict(X_test)
    return LightGBMBenchmarkResult(
        model=model,
        feature_cols=feature_cols,
        target_col=target_col,
        train_end=train_end,
        valid_end=valid_end,
        X_train=X_train,
        X_valid=X_valid,
        X_test=X_test,
        y_train=y_train,
        y_valid=y_valid,
        y_test=y_test,
        valid_pred=valid_pred,
        test_pred=test_pred,
    )


def print_lightgbm_metrics(result: LightGBMBenchmarkResult) -> None:
    yv, yt = result.y_valid.values, result.y_test.values
    print("Validation MAE:", mean_absolute_error(yv, result.valid_pred))
    print("Validation RMSE:", rmse(yv, result.valid_pred))
    print("Test MAE:", mean_absolute_error(yt, result.test_pred))
    print("Test RMSE:", rmse(yt, result.test_pred))
