from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
from entsoe import EntsoePandasClient
from entsoe.exceptions import NoMatchingDataError
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .cache import cache_to_db

OBSERVATION_COLUMNS = {
    "day_ahead_price",
    "load_forecast",
    "wind_forecast",
    "solar_forecast",
}

BIDDING_ZONE_ALIASES = {
    # ENTSO-E often expects bidding-zone EIC aliases instead of plain country codes.
    "DE": "DE_LU",
    "IT": "IT_NORD",
}


def _as_utc_index(series_or_df: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    if series_or_df.index.tz is None:
        series_or_df.index = series_or_df.index.tz_localize("UTC")
    else:
        series_or_df.index = series_or_df.index.tz_convert("UTC")
    return series_or_df.sort_index()


def _safe_float(value) -> Optional[float]:
    if pd.isna(value):
        return None
    return float(value)


def resolve_bidding_zone_code(country_code: str) -> str:
    code = str(country_code).strip().upper()
    return BIDDING_ZONE_ALIASES.get(code, code)


def _coerce_single_column_frame(
    data: pd.Series | pd.DataFrame,
    target_column: str,
    preferred_tokens: tuple[str, ...] = (),
) -> pd.DataFrame:
    """
    Normalize ENTSO-E responses that can be either a Series or DataFrame.
    """
    if isinstance(data, pd.Series):
        series = _as_utc_index(data)
        series.name = target_column
        return series.to_frame()

    frame = _as_utc_index(data.copy())
    if target_column in frame.columns:
        return frame[[target_column]]

    if len(frame.columns) == 1:
        return frame.rename(columns={frame.columns[0]: target_column})[[target_column]]

    def _best_column(candidates: list) -> Optional[str]:
        if not candidates:
            return None
        # Prefer the candidate with most available points.
        return max(candidates, key=lambda col: int(frame[col].notna().sum()))

    lowered = {col: str(col).lower() for col in frame.columns}
    preferred_candidates = []
    for token in preferred_tokens:
        preferred_candidates.extend([col for col, col_lc in lowered.items() if token in col_lc])

    preferred_col = _best_column(preferred_candidates)
    if preferred_col is not None:
        return frame.rename(columns={preferred_col: target_column})[[target_column]]

    any_col = _best_column(list(frame.columns))
    if any_col is not None:
        return frame.rename(columns={any_col: target_column})[[target_column]]

    first_col = frame.columns[0]
    return frame.rename(columns={first_col: target_column})[[target_column]]


def _normalize_utc_bounds(start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if start_ts.tz is None:
        start_ts = start_ts.tz_localize("UTC")
    else:
        start_ts = start_ts.tz_convert("UTC")
    if end_ts.tz is None:
        end_ts = end_ts.tz_localize("UTC")
    else:
        end_ts = end_ts.tz_convert("UTC")
    return start_ts, end_ts


def _empty_hourly_frame(
    columns: list[str], start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    start_ts, end_ts = _normalize_utc_bounds(start, end)
    idx = pd.date_range(start=start_ts, end=end_ts, freq="h", inclusive="left")
    return pd.DataFrame(index=idx, columns=columns)


def _coalesce_duplicate_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse duplicate column labels by taking the first non-null per row.
    """
    if frame.columns.is_unique:
        return frame

    merged: dict[str, pd.Series] = {}
    for col in frame.columns.unique():
        same_name = frame.loc[:, frame.columns == col]
        if isinstance(same_name, pd.Series):
            merged[str(col)] = same_name
        else:
            merged[str(col)] = same_name.bfill(axis=1).iloc[:, 0]
    return pd.DataFrame(merged, index=frame.index)


def _missing_ranges(missing_index: pd.DatetimeIndex) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    if missing_index.empty:
        return []
    missing_index = missing_index.sort_values().unique()
    ranges: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    current_start = missing_index[0]
    prev = missing_index[0]
    step = pd.Timedelta(hours=1)

    for ts in missing_index[1:]:
        if ts - prev != step:
            ranges.append((current_start, prev + step))
            current_start = ts
        prev = ts
    ranges.append((current_start, prev + step))
    return ranges


@dataclass
class EntsoeDataService:
    client: EntsoePandasClient
    engine: Engine
    cache_ttl_hours: Optional[int] = 24

    def __post_init__(self) -> None:
        self.get_day_ahead_prices = cache_to_db(
            self.engine, "entsoe", ttl_hours=self.cache_ttl_hours
        )(self._get_day_ahead_prices_impl)
        self.get_load_forecast = cache_to_db(
            self.engine, "entsoe", ttl_hours=self.cache_ttl_hours
        )(self._get_load_forecast_impl)
        self.get_wind_solar_forecast = cache_to_db(
            self.engine, "entsoe", ttl_hours=self.cache_ttl_hours
        )(self._get_wind_solar_forecast_impl)

    def resolve_country_code(self, country_code: str) -> str:
        return resolve_bidding_zone_code(country_code)

    def _get_day_ahead_prices_impl(
        self, country_code: str, start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.Series:
        df = self._fetch_inputs_with_secondary_cache(
            country_code=country_code,
            start=start,
            end=end,
            required_columns=["day_ahead_price"],
            api_fetcher=self._query_day_ahead_prices,
        )
        return df["day_ahead_price"]

    def _get_load_forecast_impl(
        self, country_code: str, start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.Series:
        df = self._fetch_inputs_with_secondary_cache(
            country_code=country_code,
            start=start,
            end=end,
            required_columns=["load_forecast"],
            api_fetcher=self._query_load_forecast,
        )
        return df["load_forecast"]

    def _get_wind_solar_forecast_impl(
        self, country_code: str, start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        return self._fetch_inputs_with_secondary_cache(
            country_code=country_code,
            start=start,
            end=end,
            required_columns=["wind_forecast", "solar_forecast"],
            api_fetcher=self._query_wind_solar_forecast,
        )

    def _query_day_ahead_prices(
        self, country_code: str, start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        try:
            raw = self.client.query_day_ahead_prices(country_code, start=start, end=end)
        except NoMatchingDataError:
            return _empty_hourly_frame(["day_ahead_price"], start, end)
        return _coerce_single_column_frame(
            raw,
            target_column="day_ahead_price",
            preferred_tokens=("price", "ahead"),
        )

    def _query_load_forecast(
        self, country_code: str, start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        try:
            raw = self.client.query_load_forecast(country_code, start=start, end=end)
        except NoMatchingDataError:
            return _empty_hourly_frame(["load_forecast"], start, end)
        return _coerce_single_column_frame(
            raw,
            target_column="load_forecast",
            preferred_tokens=("load",),
        )

    def _query_wind_solar_forecast(
        self, country_code: str, start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        try:
            df = self.client.query_wind_and_solar_forecast(country_code, start=start, end=end)
        except NoMatchingDataError:
            return _empty_hourly_frame(["wind_forecast", "solar_forecast"], start, end)
        df = _as_utc_index(df)
        if isinstance(df, pd.Series):
            df = df.to_frame()

        renamed = {}
        for column in df.columns:
            lc = str(column).lower()
            if "wind" in lc:
                renamed[column] = "wind_forecast"
            elif "solar" in lc:
                renamed[column] = "solar_forecast"
        df = df.rename(columns=renamed)
        df = _coalesce_duplicate_columns(df)

        if "wind_forecast" not in df.columns:
            df["wind_forecast"] = None
        if "solar_forecast" not in df.columns:
            df["solar_forecast"] = None

        return df[["wind_forecast", "solar_forecast"]]

    def _load_observations(
        self,
        country_code: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        columns: list[str],
    ) -> pd.DataFrame:
        invalid = [col for col in columns if col not in OBSERVATION_COLUMNS]
        if invalid:
            raise ValueError(f"Unsupported observation columns requested: {invalid}")

        sql_columns = ", ".join(columns)
        query = text(
            f"""
            SELECT delivery_start, {sql_columns}
            FROM electricity_market_observations
            WHERE country_code = :country_code
              AND delivery_start >= :start_ts
              AND delivery_start < :end_ts
            ORDER BY delivery_start
            """
        )

        with self.engine.begin() as conn:
            rows = conn.execute(
                query,
                {"country_code": country_code, "start_ts": start, "end_ts": end},
            ).fetchall()

        if not rows:
            return pd.DataFrame(columns=columns, index=pd.DatetimeIndex([], tz="UTC"))

        db_frame = pd.DataFrame(rows, columns=["delivery_start", *columns])
        db_frame["delivery_start"] = pd.to_datetime(db_frame["delivery_start"], utc=True)
        db_frame = db_frame.set_index("delivery_start").sort_index()
        return db_frame

    def _fetch_inputs_with_secondary_cache(
        self,
        country_code: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        required_columns: list[str],
        api_fetcher,
    ) -> pd.DataFrame:
        start_ts, end_ts = _normalize_utc_bounds(start, end)
        expected_index = pd.date_range(start=start_ts, end=end_ts, freq="h", inclusive="left")
        from_observations = self._load_observations(country_code, start_ts, end_ts, required_columns)

        if from_observations.empty:
            complete_index = pd.DatetimeIndex([], tz="UTC")
        else:
            complete_mask = from_observations[required_columns].notna().all(axis=1)
            complete_index = from_observations.index[complete_mask]

        missing_index = expected_index.difference(complete_index)

        fetched_parts: list[pd.DataFrame] = []
        for missing_start, missing_end in _missing_ranges(missing_index):
            fetched = api_fetcher(country_code, missing_start, missing_end)
            fetched = fetched.reindex(columns=required_columns)
            fetched_parts.append(fetched)

        if fetched_parts:
            fetched_frame = pd.concat(fetched_parts).sort_index()
            self.upsert_raw_data(country_code=country_code, frame=fetched_frame)
        else:
            fetched_frame = pd.DataFrame(columns=required_columns, index=pd.DatetimeIndex([], tz="UTC"))

        combined = pd.concat([from_observations, fetched_frame]).sort_index()
        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.reindex(expected_index)
        return combined[required_columns]

    def fetch_inputs(
        self, country_code: str, start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        resolved_country_code = self.resolve_country_code(country_code)
        price = _coerce_single_column_frame(
            self.get_day_ahead_prices(resolved_country_code, start, end),
            target_column="day_ahead_price",
            preferred_tokens=("price", "ahead"),
        )
        load = _coerce_single_column_frame(
            self.get_load_forecast(resolved_country_code, start, end),
            target_column="load_forecast",
            preferred_tokens=("load",),
        )
        wind_solar = self.get_wind_solar_forecast(resolved_country_code, start, end)
        df = price.join(load, how="outer").join(wind_solar, how="outer").sort_index()
        return df

    def upsert_raw_data(self, country_code: str, frame: pd.DataFrame) -> None:
        rows = []
        for ts, row in frame.iterrows():
            rows.append(
                {
                    "country_code": country_code,
                    "delivery_start": ts.to_pydatetime(),
                    "day_ahead_price": _safe_float(row.get("day_ahead_price")),
                    "load_forecast": _safe_float(row.get("load_forecast")),
                    "wind_forecast": _safe_float(row.get("wind_forecast")),
                    "solar_forecast": _safe_float(row.get("solar_forecast")),
                }
            )

        if not rows:
            return

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO electricity_market_observations (
                        country_code,
                        delivery_start,
                        day_ahead_price,
                        load_forecast,
                        wind_forecast,
                        solar_forecast
                    ) VALUES (
                        :country_code,
                        :delivery_start,
                        :day_ahead_price,
                        :load_forecast,
                        :wind_forecast,
                        :solar_forecast
                    )
                    ON CONFLICT (country_code, delivery_start) DO UPDATE
                    SET day_ahead_price = COALESCE(EXCLUDED.day_ahead_price, electricity_market_observations.day_ahead_price),
                        load_forecast = COALESCE(EXCLUDED.load_forecast, electricity_market_observations.load_forecast),
                        wind_forecast = COALESCE(EXCLUDED.wind_forecast, electricity_market_observations.wind_forecast),
                        solar_forecast = COALESCE(EXCLUDED.solar_forecast, electricity_market_observations.solar_forecast),
                        ingested_at = NOW()
                    """
                ),
                rows,
            )
