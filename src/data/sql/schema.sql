CREATE TABLE IF NOT EXISTS underlyings (
                                           id SERIAL PRIMARY KEY,
                                           symbol TEXT UNIQUE NOT NULL,
                                           exchange TEXT,
                                           currency TEXT,
                                           created_at TIMESTAMP DEFAULT NOW()
    );

CREATE TABLE IF NOT EXISTS option_contracts (
                                                id SERIAL PRIMARY KEY,
                                                underlying_id INTEGER NOT NULL REFERENCES underlyings(id),
    option_type TEXT NOT NULL CHECK (option_type IN ('call', 'put')),
    strike NUMERIC NOT NULL,
    expiration_date DATE NOT NULL,
    style TEXT,
    contract_symbol TEXT,
    UNIQUE (underlying_id, option_type, strike, expiration_date)
    );

CREATE TABLE IF NOT EXISTS option_quotes (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES option_contracts(id),
    quote_timestamp TIMESTAMP NOT NULL,
    bid NUMERIC,
    ask NUMERIC,
    mid NUMERIC,
    last_price NUMERIC,
    implied_vol NUMERIC,
    volume INTEGER,
    open_interest INTEGER,
    UNIQUE (contract_id, quote_timestamp)
    );

CREATE TABLE IF NOT EXISTS underlying_prices (
    id SERIAL PRIMARY KEY,
    underlying_id INTEGER NOT NULL REFERENCES underlyings(id),
    price_timestamp TIMESTAMP NOT NULL,
    price NUMERIC NOT NULL,
    UNIQUE (underlying_id, price_timestamp)
    );

CREATE INDEX IF NOT EXISTS idx_option_quotes_timestamp
    ON option_quotes(quote_timestamp);

CREATE INDEX IF NOT EXISTS idx_option_quotes_contract_id
    ON option_quotes(contract_id);

CREATE INDEX IF NOT EXISTS idx_option_contracts_underlying_expiry
    ON option_contracts(underlying_id, expiration_date);