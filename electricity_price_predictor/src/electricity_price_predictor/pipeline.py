from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from entsoe import EntsoePandasClient
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .entsoe_api import EntsoeDataService
from .features import build_feature_frame


def _safe_float(value) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _validate_inputs_have_signal(inputs: pd.DataFrame, country_code: str) -> None:
    required = ["day_ahead_price", "load_forecast", "wind_forecast", "solar_forecast"]
    non_null_counts = {col: int(inputs[col].notna().sum()) for col in required if col in inputs.columns}
    if non_null_counts and all(count == 0 for count in non_null_counts.values()):
        raise ValueError(
            "No ENTSO-E data available for "
            f"'{country_code}' in the requested time window. "
            "Try another bidding zone/time range, and ensure the API key has access."
        )


def persist_feature_frame(engine: Engine, country_code: str, feature_frame: pd.DataFrame) -> None:
    # Feature-store schema expects core numeric fields to be non-null.
    # Keep NaNs in the returned DataFrame, but skip incomplete rows on DB write.
    persistable = feature_frame.dropna(
        subset=["day_ahead_price", "load_forecast", "wind_forecast", "solar_forecast", "residual_load"]
    )

    rows = []
    for ts, row in persistable.iterrows():
        lag_price = [float(row[f"lagged_price_{lag}"]) for lag in range(1, 25)]
        lag_residual = [float(row[f"lagged_residual_load_{lag}"]) for lag in range(1, 25)]

        rows.append(
            {
                "country_code": country_code,
                "delivery_start": ts.to_pydatetime(),
                "day_ahead_price": float(row["day_ahead_price"]),
                "load_forecast": _safe_float(row["load_forecast"]),
                "wind_forecast": _safe_float(row["wind_forecast"]),
                "solar_forecast": _safe_float(row["solar_forecast"]),
                "residual_load": _safe_float(row["residual_load"]),
                "lagged_price": lag_price,
                "lagged_residual_load": lag_residual,
                "hour_of_day_sin": float(row["hour_of_day_sin"]),
                "hour_of_day_cos": float(row["hour_of_day_cos"]),
                "weekday_sin": float(row["weekday_sin"]),
                "weekday_cos": float(row["weekday_cos"]),
                "month_sin": float(row["month_sin"]),
                "month_cos": float(row["month_cos"]),
                "feature_version": "v1",
                "created_at": datetime.now(timezone.utc),
            }
        )

    if not rows:
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO electricity_price_features (
                    country_code,
                    delivery_start,
                    day_ahead_price,
                    load_forecast,
                    wind_forecast,
                    solar_forecast,
                    residual_load,
                    lagged_price,
                    lagged_residual_load,
                    hour_of_day_sin,
                    hour_of_day_cos,
                    weekday_sin,
                    weekday_cos,
                    month_sin,
                    month_cos,
                    feature_version,
                    created_at
                ) VALUES (
                    :country_code,
                    :delivery_start,
                    :day_ahead_price,
                    :load_forecast,
                    :wind_forecast,
                    :solar_forecast,
                    :residual_load,
                    :lagged_price,
                    :lagged_residual_load,
                    :hour_of_day_sin,
                    :hour_of_day_cos,
                    :weekday_sin,
                    :weekday_cos,
                    :month_sin,
                    :month_cos,
                    :feature_version,
                    :created_at
                )
                ON CONFLICT (country_code, delivery_start, feature_version) DO UPDATE
                SET day_ahead_price = EXCLUDED.day_ahead_price,
                    load_forecast = EXCLUDED.load_forecast,
                    wind_forecast = EXCLUDED.wind_forecast,
                    solar_forecast = EXCLUDED.solar_forecast,
                    residual_load = EXCLUDED.residual_load,
                    lagged_price = EXCLUDED.lagged_price,
                    lagged_residual_load = EXCLUDED.lagged_residual_load,
                    hour_of_day_sin = EXCLUDED.hour_of_day_sin,
                    hour_of_day_cos = EXCLUDED.hour_of_day_cos,
                    weekday_sin = EXCLUDED.weekday_sin,
                    weekday_cos = EXCLUDED.weekday_cos,
                    month_sin = EXCLUDED.month_sin,
                    month_cos = EXCLUDED.month_cos,
                    created_at = EXCLUDED.created_at
                """
            ),
            rows,
        )


def run_feature_pipeline(
    engine: Engine,
    entsoe_api_key: str,
    country_code: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    cache_ttl_hours: int = 24,
) -> pd.DataFrame:
    client = EntsoePandasClient(api_key=entsoe_api_key)
    service = EntsoeDataService(client=client, engine=engine, cache_ttl_hours=cache_ttl_hours)
    resolved_country_code = service.resolve_country_code(country_code)
    inputs = service.fetch_inputs(country_code=resolved_country_code, start=start, end=end)
    _validate_inputs_have_signal(inputs, resolved_country_code)
    service.upsert_raw_data(country_code=resolved_country_code, frame=inputs)
    features = build_feature_frame(inputs)
    persist_feature_frame(engine, country_code=resolved_country_code, feature_frame=features)
    return features
