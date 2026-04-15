from sqlalchemy import create_engine
from option_pricing.src.data.ingestion.config.settings import DB_CONFIG

def build_db_url() -> str:
    return (
        f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )

def db_engine():
    db_url = build_db_url()
    engine = create_engine(db_url, future=True)
    return engine
