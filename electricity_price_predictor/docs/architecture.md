# Architecture Notes

This document is the quick architecture map. For full file-by-file implementation details, see `docs/developer_guide.md`.

## End-to-end data flow

1. `scripts/build_feature_store.py` parses CLI arguments and validates env vars.
2. It calls `pipeline.run_feature_pipeline(...)`.
3. `EntsoeDataService.fetch_inputs(...)` loads:
   - `day_ahead_price`
   - `load_forecast`
   - `wind_forecast`
   - `solar_forecast`
4. Each ENTSO-E call is wrapped by `cache_to_db(...)` and either:
   - serves a hit from `entsoe_api_cache`, or
   - falls back to `electricity_market_observations` for already-known timestamps,
   - and performs API calls only for missing hourly intervals.
5. Missing intervals returned from API are upserted into `electricity_market_observations`.
6. The final merged result is cached in `entsoe_api_cache`.
7. Raw merged series are upserted to `electricity_market_observations`.
8. `features.build_feature_frame(...)` computes:
   - `residual_load`
   - lagged arrays (24 values each)
   - cyclical encodings for hour/weekday/month
   - preserves `NaN` for missing forecast-derived values.
9. `pipeline.persist_feature_frame(...)` upserts model-ready rows to `electricity_price_features`.
   - filters out rows that violate feature-table NOT NULL constraints.

## Process diagram

```mermaid
flowchart TD
    A[build_feature_store.py CLI] --> B[run_feature_pipeline]
    B --> C[EntsoeDataService.fetch_inputs]
    C --> D{Hit in entsoe_api_cache?}
    D -->|Yes| E[Load payload from entsoe_api_cache]
    D -->|No| F[Read electricity_market_observations]
    F --> G{Missing hourly timestamps?}
    G -->|No| H[Reuse DB observation rows]
    G -->|Yes| I[Call ENTSO-E only for missing ranges]
    I --> I2{NoMatchingDataError?}
    I2 -->|Yes| I3[Use empty hourly frame for endpoint]
    I2 -->|No| I4[Normalize payload]
    I4 --> I5[Coalesce duplicate columns by first non-null]
    I3 --> J[Upsert missing rows to electricity_market_observations]
    I5 --> J
    H --> K[Build merged input DataFrame]
    J --> K
    K --> L[Store payload in entsoe_api_cache]
    E --> M[Use cached input DataFrame]
    L --> N[Upsert electricity_market_observations]
    M --> N
    N --> O[build_feature_frame]
    O --> P[Create lags + cyclical features]
    P --> P2[Preserve NaN in forecast-derived columns]
    P2 --> P3[Drop rows missing day_ahead_price or lagged_price_1..24]
    P3 --> Q[Upsert persistable subset into electricity_price_features]
```

## Key design reasons

- DB cache avoids repeated ENTSO-E calls during iterative model work.
- Observation-table fallback avoids re-fetching timestamps already persisted once.
- Pickled payloads preserve exact pandas object shape and index information.
- Feature table stores fixed-size lag arrays so one row corresponds to one prediction timestamp.
- Missing forecasts are kept as `NaN` in analysis outputs, avoiding misleading zero-imputation.
- Persistence layer enforces schema compatibility by skipping rows with nulls in NOT NULL feature columns.

## Extension points

- Add label/target tables (`t+1`, `t+24`, etc.).
- Add training metadata + model registry tables.
- Add partitioning strategy for multi-year production-scale data.
