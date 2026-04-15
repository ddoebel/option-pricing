from __future__ import annotations

import math

import pandas as pd


def _cyclical_encode(values: pd.Series, period: int, prefix: str) -> pd.DataFrame:
    angle = 2.0 * math.pi * values / period
    return pd.DataFrame(
        {f"{prefix}_sin": angle.apply(math.sin), f"{prefix}_cos": angle.apply(math.cos)},
        index=values.index,
    )


def build_feature_frame(inputs: pd.DataFrame, max_lag: int = 24) -> pd.DataFrame:
    """
    Build feature set for electricity price forecasting.

    Included:
    - day_ahead_price, load_forecast, wind_forecast, solar_forecast
    - residual_load
    - lagged_price(t-1..t-24)
    - lagged_residual_load(t-1..t-24)
    - hour/week_day/month cyclical encodings
    """
    df = inputs.copy().sort_index()
    required = {"day_ahead_price", "load_forecast", "wind_forecast", "solar_forecast"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required input columns: {sorted(missing)}")

    # Preserve source missingness semantics for downstream users.
    # We keep NaNs instead of imputing to 0.0 so missing data is explicit.
    df["residual_load"] = df["load_forecast"] - df["wind_forecast"] - df["solar_forecast"]

    for lag in range(1, max_lag + 1):
        df[f"lagged_price_{lag}"] = df["day_ahead_price"].shift(lag)
        df[f"lagged_residual_load_{lag}"] = df["residual_load"].shift(lag)

    time_index = df.index
    if time_index.tz is None:
        time_index = time_index.tz_localize("UTC")
    else:
        time_index = time_index.tz_convert("UTC")

    cyclical = [
        _cyclical_encode(pd.Series(time_index.hour, index=df.index), 24, "hour_of_day"),
        _cyclical_encode(pd.Series(time_index.weekday, index=df.index), 7, "weekday"),
        _cyclical_encode(pd.Series(time_index.month - 1, index=df.index), 12, "month"),
    ]
    for cyc in cyclical:
        df = df.join(cyc)

    # Only enforce warmup/history constraints for price lags.
    # Other feature columns can remain NaN when source data is missing.
    required_for_row = ["day_ahead_price", *[f"lagged_price_{lag}" for lag in range(1, max_lag + 1)]]
    return df.dropna(subset=required_for_row).sort_index()
