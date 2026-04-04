import pandas as pd

from src.data.ingestion.db_connect import db_engine


def fetch_underlyings() -> pd.DataFrame:
    """
    Fetch all entries from the underlyings table using configured DB credentials.
    """
    engine = db_engine()
    return pd.read_sql("SELECT * FROM underlyings;", engine)


if __name__ == "__main__":
    print(fetch_underlyings())