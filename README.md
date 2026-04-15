# option_pricing

C++/Python quantitative finance engine for option pricing, implied-volatility analysis, and market-data ingestion.

## What is included

- `cpp/`: core C++ pricing library (Monte Carlo + Black-Scholes closed form), DB ingestion hooks, and pybind bindings.
- `qengine/`: Python package exposing the native extension (`import qengine`).
- `src/ImpliedVolatility/`: SVI calibration and implied-volatility tooling.
- `src/data/`: data ingestion, SQL schema, and analytics helpers.
- `tests/`: C++ unit tests (GoogleTest).
- `scripts/`: operational scripts, including PostgreSQL setup.
- `docs/`: Doxygen configuration and generated API docs (ignored in git for publication).

## Quickstart

### 1) Clone and create a Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
pip install pandas yfinance sqlalchemy psycopg2-binary matplotlib scipy
```

### 2) Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env` with your local database credentials.

### 3) Create database and schema

Use the idempotent setup script:

```bash
source .env
python scripts/setup_postgres.py
```

This script creates/updates:
- database role (`DB_USER`)
- database (`DB_NAME`)
- tables/indexes from `src/data/sql/schema.sql`

### 4) Build C++ extension and run tests

```bash
cmake -S . -B build
cmake --build build -j
ctest --test-dir build --output-on-failure
```

### 5) Run Yahoo options ingestion

```bash
source .env
python src/data/ingestion/ingest_yahoo_options.py
```

`PIPELINE_SYMBOLS` in `.env` controls which symbols are ingested (comma-separated, e.g. `SPY,AAPL,QQQ`).

## Security and publication notes

- No credentials are stored in source code.
- `.env` files are git-ignored; only `.env.example` is committed.
- Before publishing, rotate any credentials that were ever committed in the past.
- Prefer least-privilege DB users for runtime ingestion jobs.

## Generating C++ API docs

```bash
cmake --build build --target docs
```

Generated output goes to `docs/html/` and is ignored in version control.
