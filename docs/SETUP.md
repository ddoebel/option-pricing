# Setup Guide

This guide describes a clean local setup for development and reproducible runs.

## Prerequisites

- Python 3.10+
- CMake 3.16+
- A C++20 compiler
- PostgreSQL 14+ (or Docker)
- On macOS, Homebrew packages for C++ DB support:
  - `libpq`
  - `libpqxx`
  - `eigen`
  - `pybind11`

## Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
pip install pandas yfinance sqlalchemy psycopg2-binary matplotlib scipy
```

## Environment configuration

```bash
cp .env.example .env
```

Edit `.env` and set:

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `PIPELINE_SYMBOLS`
- admin credentials used only by setup script (`POSTGRES_ADMIN_*`)

## Database bootstrap

```bash
source .env
python scripts/setup_postgres.py
```

The script is idempotent and safe to rerun.

## Build and test C++

```bash
cmake -S . -B build
cmake --build build -j
ctest --test-dir build --output-on-failure
```

## Generate Doxygen docs

```bash
cmake --build build --target docs
```
