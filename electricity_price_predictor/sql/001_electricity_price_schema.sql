CREATE TABLE IF NOT EXISTS entsoe_api_cache (
    cache_key TEXT PRIMARY KEY,
    namespace TEXT NOT NULL,
    function_name TEXT NOT NULL,
    args_json JSONB NOT NULL,
    payload BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_entsoe_api_cache_namespace_fn
    ON entsoe_api_cache(namespace, function_name);

CREATE INDEX IF NOT EXISTS idx_entsoe_api_cache_expires_at
    ON entsoe_api_cache(expires_at);

CREATE TABLE IF NOT EXISTS electricity_market_observations (
    country_code TEXT NOT NULL,
    delivery_start TIMESTAMPTZ NOT NULL,
    day_ahead_price DOUBLE PRECISION,
    load_forecast DOUBLE PRECISION,
    wind_forecast DOUBLE PRECISION,
    solar_forecast DOUBLE PRECISION,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (country_code, delivery_start)
);

CREATE INDEX IF NOT EXISTS idx_electricity_market_observations_delivery
    ON electricity_market_observations(delivery_start);

CREATE TABLE IF NOT EXISTS electricity_price_features (
    country_code TEXT NOT NULL,
    delivery_start TIMESTAMPTZ NOT NULL,
    day_ahead_price DOUBLE PRECISION NOT NULL,
    load_forecast DOUBLE PRECISION NOT NULL,
    wind_forecast DOUBLE PRECISION NOT NULL,
    solar_forecast DOUBLE PRECISION NOT NULL,
    residual_load DOUBLE PRECISION NOT NULL,
    lagged_price DOUBLE PRECISION[] NOT NULL,
    lagged_residual_load DOUBLE PRECISION[] NOT NULL,
    hour_of_day_sin DOUBLE PRECISION NOT NULL,
    hour_of_day_cos DOUBLE PRECISION NOT NULL,
    weekday_sin DOUBLE PRECISION NOT NULL,
    weekday_cos DOUBLE PRECISION NOT NULL,
    month_sin DOUBLE PRECISION NOT NULL,
    month_cos DOUBLE PRECISION NOT NULL,
    feature_version TEXT NOT NULL DEFAULT 'v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (country_code, delivery_start, feature_version),
    CONSTRAINT chk_lagged_price_len CHECK (CARDINALITY(lagged_price) = 24),
    CONSTRAINT chk_lagged_residual_load_len CHECK (CARDINALITY(lagged_residual_load) = 24)
);

CREATE INDEX IF NOT EXISTS idx_electricity_price_features_delivery
    ON electricity_price_features(delivery_start);
