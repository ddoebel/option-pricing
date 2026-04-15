#!/usr/bin/env python3
"""
Idempotent PostgreSQL bootstrap script for the option_pricing project.

What it does:
1) Creates the project role if it does not exist.
2) Creates the project database if it does not exist.
3) Grants ownership/privileges.
4) Applies src/data/sql/schema.sql to the project database.

Configuration comes from environment variables (see .env.example).
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg2
from psycopg2 import sql


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "src" / "data" / "sql" / "schema.sql"


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def admin_connect(dbname: str):
    return psycopg2.connect(
        dbname=dbname,
        user=_env("POSTGRES_ADMIN_USER", "postgres"),
        password=_env("POSTGRES_ADMIN_PASSWORD", "postgres"),
        host=_env("POSTGRES_ADMIN_HOST", "localhost"),
        port=_env("POSTGRES_ADMIN_PORT", "5432"),
    )


def ensure_role_and_database() -> None:
    db_user = _env("DB_USER", "quant_user")
    db_password = _env("DB_PASSWORD", "")
    db_name = _env("DB_NAME", "options_db")

    admin_db = _env("POSTGRES_ADMIN_DB", "postgres")
    with admin_connect(admin_db) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (db_user,))
            role_exists = cur.fetchone() is not None
            if not role_exists:
                cur.execute(
                    sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD %s").format(
                        sql.Identifier(db_user)
                    ),
                    (db_password,),
                )
            else:
                cur.execute(
                    sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD %s").format(
                        sql.Identifier(db_user)
                    ),
                    (db_password,),
                )

            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            db_exists = cur.fetchone() is not None
            if not db_exists:
                cur.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(db_name),
                        sql.Identifier(db_user),
                    )
                )
            else:
                cur.execute(
                    sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
                        sql.Identifier(db_name),
                        sql.Identifier(db_user),
                    )
                )


def apply_schema() -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with admin_connect(_env("DB_NAME", "options_db")) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(schema_sql)


def main() -> None:
    print("Ensuring role/database exist...")
    ensure_role_and_database()
    print("Applying schema...")
    apply_schema()
    print("Database setup complete.")


if __name__ == "__main__":
    main()
