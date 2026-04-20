"""Leakage-aware GAM + AR(p) on GAM residuals (refactored from analyze_data notebook)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd
from pygam import LinearGAM, s
from statsmodels.tsa.ar_model import AutoReg


ForecastMode = Literal["recursive", "rolling_one_step"]


def _build_default_gam_terms(n_features: int) -> Any:
    terms = s(0)
    for i in range(1, n_features):
        terms = terms + s(i)
    return terms


@dataclass
class GamAr1AdditiveModel:
    """
    Fit GAM on training slice only; fit AR on training residuals; build full-series additive forecast.

    Use :meth:`fit` then :meth:`predict_additive` to mirror train vs inference timing in benchmarks.
    """

    target_col: str = "day_ahead_price"
    gam_feature_cols: tuple[str, ...] = ("hour_sin", "hour_cos")
    ar_lags: int = 1
    gam_terms: Any | None = None
    forecast_mode: ForecastMode = "rolling_one_step"

    gam_: LinearGAM | None = None
    ar_model_: Any | None = None
    train_end_: int | None = None
    valid_end_: int | None = None
    df_work_: pd.DataFrame | None = None
    X_all_: np.ndarray | None = None
    y_all_: np.ndarray | None = None

    def _ensure_seasonal_features(self, df_work: pd.DataFrame) -> pd.DataFrame:
        if "hour_sin" in self.gam_feature_cols and "hour_sin" not in df_work.columns:
            hour = df_work.index.hour
            df_work = df_work.copy()
            df_work["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        if "hour_cos" in self.gam_feature_cols and "hour_cos" not in df_work.columns:
            hour = df_work.index.hour
            df_work = df_work.copy()
            df_work["hour_cos"] = np.cos(2 * np.pi * hour / 24)
        if "t" in self.gam_feature_cols and "t" not in df_work.columns:
            df_work = df_work.copy()
            df_work["t"] = np.arange(len(df_work), dtype=float)
        return df_work

    def fit(
        self,
        df: pd.DataFrame,
        *,
        train_end: int,
        valid_end: int,
    ) -> GamAr1AdditiveModel:
        df_work = df.copy().sort_index()
        n = len(df_work)
        if n < max(10, self.ar_lags + 5):
            raise ValueError(f"Not enough rows for ar_lags={self.ar_lags}: n={n}")
        if not (0 < train_end < valid_end < n):
            raise ValueError(
                f"Invalid split: train_end={train_end}, valid_end={valid_end}, n={n}. "
                "Need 0 < train_end < valid_end < n."
            )

        df_work = self._ensure_seasonal_features(df_work)
        required = list(self.gam_feature_cols) + [self.target_col]
        missing = [c for c in required if c not in df_work.columns]
        if missing:
            raise KeyError(f"Missing required columns in df: {missing}")

        X_all = df_work[list(self.gam_feature_cols)].values
        y_all = df_work[self.target_col].values

        X_train = X_all[:train_end]
        y_train = y_all[:train_end]

        gam_terms = self.gam_terms if self.gam_terms is not None else _build_default_gam_terms(X_all.shape[1])
        gam = LinearGAM(gam_terms).fit(X_train, y_train)

        y_pred_train = gam.predict(X_train)
        resid_train = y_train - y_pred_train
        resid_train_s = pd.Series(resid_train, index=df_work.index[:train_end])
        ar_model = AutoReg(resid_train_s, lags=self.ar_lags, old_names=False).fit()

        self.gam_ = gam
        self.ar_model_ = ar_model
        self.train_end_ = train_end
        self.valid_end_ = valid_end
        self.df_work_ = df_work
        self.X_all_ = X_all
        self.y_all_ = y_all
        return self

    def predict_additive(self) -> pd.Series:
        if self.gam_ is None or self.ar_model_ is None or self.df_work_ is None:
            raise RuntimeError("Call fit() before predict_additive().")
        assert self.X_all_ is not None and self.y_all_ is not None
        assert self.train_end_ is not None

        gam = self.gam_
        ar_model = self.ar_model_
        train_end = self.train_end_
        df_work = self.df_work_
        X_all = self.X_all_
        y_all = self.y_all_
        n = len(y_all)
        ar_lags = self.ar_lags

        y_pred_all = gam.predict(X_all)
        params_arr = np.asarray(ar_model.params, dtype=float)
        intercept = float(params_arr[0])
        phi = params_arr[1 : 1 + ar_lags]

        resid_true_all = y_all - y_pred_all
        fitted_resid_train = np.asarray(ar_model.fittedvalues, dtype=float)

        resid_pred = np.zeros(n, dtype=float)
        if train_end - ar_lags > 0:
            resid_pred[ar_lags:train_end] = fitted_resid_train

        resid_history = np.zeros(n, dtype=float)
        resid_history[:train_end] = y_all[:train_end] - y_pred_all[:train_end]

        if self.forecast_mode not in {"recursive", "rolling_one_step"}:
            raise ValueError("forecast_mode must be 'recursive' or 'rolling_one_step'")

        for t_idx in range(train_end, n):
            past = resid_history[t_idx - ar_lags : t_idx][::-1]
            resid_pred[t_idx] = intercept + float(np.dot(phi, past))
            if self.forecast_mode == "recursive":
                resid_history[t_idx] = resid_pred[t_idx]
            else:
                resid_history[t_idx] = resid_true_all[t_idx]

        additive = y_pred_all + resid_pred
        return pd.Series(additive, index=df_work.index, name="gam_ar1_additive_model")


def compute_additive_model_gam_ar1(
    df: pd.DataFrame,
    target_col: str = "day_ahead_price",
    gam_feature_cols: tuple[str, ...] = ("hour_sin", "hour_cos"),
    ar_lags: int = 1,
    gam_terms: Any | None = None,
    return_components: bool = False,
    train_frac: float = 0.7,
    valid_frac: float = 0.85,
    train_end: int | None = None,
    valid_end: int | None = None,
    forecast_mode: ForecastMode = "rolling_one_step",
):
    """
    Notebook-compatible API: one-shot fit + predict on full ``df``.

    Returns a ``pd.Series`` aligned to ``df`` index, optionally with diagnostics dict.
    """
    df_work = df.copy().sort_index()
    n = len(df_work)
    if train_end is None:
        train_end = int(n * train_frac)
    if valid_end is None:
        valid_end = int(n * valid_frac)

    model = GamAr1AdditiveModel(
        target_col=target_col,
        gam_feature_cols=gam_feature_cols,
        ar_lags=ar_lags,
        gam_terms=gam_terms,
        forecast_mode=forecast_mode,
    )
    model.fit(df_work, train_end=train_end, valid_end=valid_end)
    out = model.predict_additive()

    if return_components:
        assert model.gam_ is not None and model.ar_model_ is not None
        y_pred_all = model.gam_.predict(model.X_all_)
        resid_true_all = model.y_all_ - y_pred_all
        return out, {
            "gam": model.gam_,
            "ar_model": model.ar_model_,
            "y_pred_all": y_pred_all,
            "resid_true_all": resid_true_all,
            "resid_pred": out.values - y_pred_all,
        }
    return out
