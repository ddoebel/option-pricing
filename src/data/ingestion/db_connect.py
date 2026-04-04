from sqlalchemy import create_engine
from src.data.ingestion.config.settings import get_db_config


def build_db_url() -> str:
    cfg = get_db_config()
    return (
        f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    )

def db_engine():
    db_url = build_db_url()
    engine = create_engine(db_url, future=True)
    return engine
