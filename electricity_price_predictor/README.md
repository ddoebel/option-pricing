# Electricity Price Predictor

Standalone module for ENTSO-E ingestion and feature-store creation in `quant_db`.

## Start here (customer-friendly)

The fastest way to understand and demo this project is the notebook:

- **Primary walkthrough notebook:** `src/data_analysis/analyze_data.ipynb`

This notebook is the recommended entry point for business users, stakeholders, and new contributors because it shows the full flow in one place: data loading, feature preparation, model training, and evaluation outputs.

## Quick path

1. Set up the environment (see `Setup` below).
2. Build/populate the feature store (see `Build feature store` below).
3. Open and run `src/data_analysis/analyze_data.ipynb` end-to-end.

## Documentation

- High-level architecture: `docs/architecture.md`
- Detailed developer documentation (file-by-file + UML): `docs/developer_guide.md`

## What it builds

- Input columns:
  - `day_ahead_price`
  - `load_forecast`
  - `wind_forecast`
  - `solar_forecast`
- Derived columns:
  - `residual_load`
  - `lagged_price` (`t-1` ... `t-24`, stored as array length 24)
  - `lagged_residual_load` (`t-1` ... `t-24`, stored as array length 24)
  - `hour_of_day_sin`, `hour_of_day_cos`
  - `weekday_sin`, `weekday_cos`
  - `month_sin`, `month_cos`

## Column units (data dictionary)

All timestamps are hourly and stored in UTC (`delivery_start`).

- `day_ahead_price`
  - Unit: `EUR/MWh` (euros per megawatt-hour).
- `load_forecast`
  - Unit: `MW` (megawatts).
- `wind_forecast`
  - Unit: `MW` (megawatts).
- `solar_forecast`
  - Unit: `MW` (megawatts).
- `residual_load = load_forecast - wind_forecast - solar_forecast`
  - Unit: `MW` (megawatts).
- `lagged_price` (array of 24 values for `t-1..t-24`)
  - Unit: `EUR/MWh`.
- `lagged_residual_load` (array of 24 values for `t-1..t-24`)
  - Unit: `MW`.
- `hour_of_day_sin`, `hour_of_day_cos`
  - Unit: dimensionless in `[-1, 1]`.
- `weekday_sin`, `weekday_cos`
  - Unit: dimensionless in `[-1, 1]`.
- `month_sin`, `month_cos`
  - Unit: dimensionless in `[-1, 1]`.

## Missing-data semantics

The pipeline intentionally distinguishes **missing** from **measured zero**:

- Forecast columns (`load_forecast`, `wind_forecast`, `solar_forecast`) remain `NaN` when ENTSO-E has no value.
- `residual_load` is computed directly from source columns and remains `NaN` when any source component is missing.
- Feature engineering drops rows only for lag warmup requirements (`day_ahead_price` and `lagged_price_1..24`), not for every nullable forecast column.
- During DB persistence to `electricity_price_features`, rows with nulls in NOT NULL core columns are skipped (to satisfy schema constraints) while still being available in the returned in-memory DataFrame.

## Data contracts

### In-memory contract (`run_feature_pipeline(...)` return value)

- Index:
  - Type: timezone-aware `DatetimeIndex`
  - Granularity: hourly
  - Timezone: UTC
  - Uniqueness: unique timestamps expected
- Columns:
  - Base signals: `day_ahead_price`, `load_forecast`, `wind_forecast`, `solar_forecast`
  - Derived: `residual_load`
  - Lag vectors (expanded): `lagged_price_1..24`, `lagged_residual_load_1..24`
  - Cyclical: `hour_of_day_sin`, `hour_of_day_cos`, `weekday_sin`, `weekday_cos`, `month_sin`, `month_cos`
- Nullability:
  - `day_ahead_price`: required for returned rows.
  - `lagged_price_1..24`: required for returned rows.
  - `load_forecast`, `wind_forecast`, `solar_forecast`, `residual_load`, and `lagged_residual_load_*`: nullable (`NaN` allowed).

### Persistence contract (`electricity_price_features`)

- Persisted row key:
  - (`country_code`, `delivery_start`, `feature_version`)
- NOT NULL core columns in schema:
  - `day_ahead_price`, `load_forecast`, `wind_forecast`, `solar_forecast`, `residual_load`
  - `lagged_price`, `lagged_residual_load`
  - cyclical columns (`hour_of_day_*`, `weekday_*`, `month_*`)
- Write behavior:
  - The persistence layer filters out non-conforming rows (nulls in NOT NULL core columns) before UPSERT.
  - Persisted lag arrays are fixed length 24 and map to `t-1..t-24`.

### Raw observations contract (`electricity_market_observations`)

- Indexing/key semantics:
  - one row per (`country_code`, `delivery_start`)
- Update semantics:
  - partial refreshes do not overwrite existing non-null values with nulls (`COALESCE` merge policy)

## Country-code and API behavior notes

- Use ENTSO-E bidding-zone identifiers (for example `DE_LU` rather than `DE`) when querying across all endpoints.
- The pipeline includes a bidding-zone resolver for common country aliases:
  - `DE -> DE_LU`
  - `IT -> IT_NORD`
- Persistence uses the resolved bidding-zone code so DB keys match the queried market zone.
- Some ENTSO-E endpoints may return no matches for specific windows/countries. These are handled as empty hourly frames for that endpoint rather than hard-failing the whole fetch.
- Wind/solar responses can include duplicate semantic columns after normalization; the service coalesces duplicates by taking the first non-null value per timestamp.

## Database objects

`sql/001_electricity_price_schema.sql` creates:

- `entsoe_api_cache`: generic decorator cache table (pickled payloads, TTL support)
- `electricity_market_observations`: raw hourly ENTSO-E observations
- `electricity_price_features`: model-ready feature store

## Setup

```bash
cd electricity_price_predictor
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set env vars:

```bash
export ENTSOE_API_KEY="your_entsoe_key"
export QUANT_DB_HOST="localhost"
export QUANT_DB_PORT="5432"
export QUANT_DB_NAME="quant_db"
export QUANT_DB_USER="quant_user"
export QUANT_DB_PASSWORD="strong_password"
```

## Initialize schema

```bash
PYTHONPATH=src python scripts/init_db.py
```

## Build feature store

```bash
PYTHONPATH=src python scripts/build_feature_store.py \
  --country-code DE_LU \
  --start 2026-01-01T00:00:00Z \
  --end 2026-02-01T00:00:00Z \
  --cache-ttl-hours 24
```

## Decorator caching behavior

The `cache_to_db` decorator:

- hashes function name + arguments into deterministic `cache_key`
- checks `entsoe_api_cache` first
- returns cached payload if key exists and not expired
- otherwise uses `electricity_market_observations` as secondary cache at timestamp level
- only calls ENTSO-E for missing hourly intervals, then upserts those rows
- stores final returned object in `entsoe_api_cache`

This gives a two-layer cache:
1) fast function-result cache (`entsoe_api_cache`) and
2) canonical timestamp cache (`electricity_market_observations`).
