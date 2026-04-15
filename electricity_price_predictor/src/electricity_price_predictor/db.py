import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_database_url() -> str:
    """Build database URL from env or fallback defaults."""
    explicit_url = os.getenv("QUANT_DB_URL")
    if explicit_url:
        return explicit_url

    host = os.getenv("QUANT_DB_HOST", "localhost")
    port = os.getenv("QUANT_DB_PORT", "5432")
    database = os.getenv("QUANT_DB_NAME", "quant_db")
    user = os.getenv("QUANT_DB_USER", "quant_user")
    password = os.getenv("QUANT_DB_PASSWORD", "strong_password")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def get_engine(echo: bool = False) -> Engine:
    """Create SQLAlchemy engine for quant_db."""
    return create_engine(get_database_url(), future=True, echo=echo)
