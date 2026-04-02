# Option Pricing Engine with Market Data Pipeline 
👉 [Project blog](https://notes.ddoebel.de/public-folder/Option-Pricing-Engine)
## 📌 Project Description

This repository implements a **production-style quantitative valuation pipeline** for equity options, combining high-performance pricing models with a full data and calibration workflow.

The system goes beyond a standalone pricer: it integrates **market data ingestion, structured storage, numerical pricing, and volatility surface calibration** into a single reproducible framework.
### The goal of this project 

The goal of this project is to serve as a **modular foundation for quantitative modeling and experimentation** in option pricing and financial time series.

Rather than implementing a single model, the system is designed to support:

- benchmarking different pricing approaches (analytical, simulation-based, and data-driven),
- comparing numerical methods under realistic market data conditions,
- and extending toward more advanced workflows such as statistical learning and model calibration.

A key objective is to create an environment where **new ideas from research can be implemented, tested, and evaluated within a consistent pipeline**, rather than in isolated scripts or notebooks.

This includes:

- integrating alternative pricing methodologies into a shared framework,
- analyzing model behavior across time and market regimes,
- and building reproducible pipelines for both numerical and data-driven approaches.

Ultimately, the project aims to bridge:
- **theoretical models** (e.g. stochastic processes, volatility parameterizations),
- **numerical methods** (simulation, calibration),
- and **data-driven techniques** (time-series analysis, machine learning),

within a single, extensible system. Moving closer to a production-grade pipeline. 
### What the system does

The system supports the following workflow:

- Ingest listed option market data (Yahoo Finance)
- Normalize and store it in a relational database (PostgreSQL)
- Compute implied volatilities from observed prices
- Calibrate parametric volatility surfaces (SVI)
- Run pricing models (Black-Scholes, Monte Carlo)
- Expose fast pricing routines via Python for analysis and research

---
This project aims to **unify these components into a coherent system**, with clear interfaces between:

- **Data layer** (ingestion, storage, schema)
- **Model layer** (C++ pricing engines)
- **Analytics layer** (Python calibration and diagnostics)
- **Execution layer** (reproducible pipelines)

---

### Technology choices

The architecture deliberately combines multiple technologies, each chosen for a specific role:

- **C++ (C++20)**  
  Used for performance-critical pricing components (Monte Carlo, closed-form models) and clean domain modeling.

- **Python**  
  Used for orchestration, data processing, calibration (SVI), and rapid experimentation.

- **pybind11**  
  Bridges C++ and Python, enabling high-performance models to be used in flexible workflows.

- **PostgreSQL + SQLAlchemy**  
  Provides structured, queryable storage for market data and supports reproducible calibration pipelines.

---

### Key challenges addressed

This project tackles several non-trivial challenges:

- **Bridging performance and usability**  
  Integrating a C++ pricing engine into a Python-driven research pipeline.

- **Data consistency and reproducibility**  
  Designing a schema and ingestion process that supports reliable downstream calibration.

- **Implied volatility inversion and calibration**  
  Implementing stable numerical inversion and robust SVI fitting under noisy market data.

- **System design over isolated models**  
  Ensuring that data, models, and workflows interact cleanly as a unified system.

---

### Future directions

Planned improvements focus on moving further toward production-grade systems:

- Arbitrage-free implied volatility surface construction
- More robust calibration and smoothing techniques
- Performance optimization (parallel Monte Carlo, batching)
- Extension to additional data sources and APIs
- Improved testing of end-to-end data and calibration pipelines
- comparing classical stochastic models vs data-driven approaches for pricing or volatility forecasting

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

Then edit `.env` with your local database credentials (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, etc.).

Shell `VAR=value` lines are **not** exported to child processes by default. Load them into the environment for Python with:

```bash
set -a && source .env && set +a
```

Database settings are read when each connection is created, so this must succeed **before** you run `python …` (or use `export` on each line you care about).

### 3) Create database and schema

Use the idempotent setup script:

```bash
set -a && source .env && set +a
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
set -a && source .env && set +a
python src/data/ingestion/ingest_yahoo_options.py
```

`PIPELINE_SYMBOLS` in `.env` controls which symbols are ingested (comma-separated, e.g. `SPY,AAPL,QQQ`).

### 6) Run the DB → calibration demo (`load_data`)

From the parent directory of the `option_pricing` folder (so `import option_pricing` resolves), with `.env` exported as above:

```bash
set -a && source option_pricing/.env && set +a
python3 -m option_pricing.src.data.load_data
```

## Generating C++ API docs

```bash
cmake --build build --target docs
```
## 📚 Further Analysis 

A more detailed discussion of numerial stability, implied volatility inversion, and calibration challenges is available here 

👉 [Project blog](https://notes.ddoebel.de/public-folder/Option-Pricing-Engine)

This includes deeper analysis of:
- implied volatility instability from raw market data
- calibration challenges under noisy inputs
- numerical experiments and diagnostics
(see in particular [Observations and further analysis](https://notes.ddoebel.de/public-folder/Option-Pricing-Engine#-observations-and-further-analysis)) 
