from pathlib import Path

from sqlalchemy import text

from electricity_price_predictor.db import get_engine


def main() -> None:
    engine = get_engine()
    schema_path = Path(__file__).resolve().parents[1] / "sql" / "001_electricity_price_schema.sql"
    sql = schema_path.read_text(encoding="utf-8")

    with engine.begin() as conn:
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(text(stmt))

    print("Schema initialized for electricity price predictor.")


if __name__ == "__main__":
    main()
