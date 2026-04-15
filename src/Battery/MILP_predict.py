import pandas as pd
from src.data.ingestion.db_connect import db_engine

def load_dataframe(series_id : int):
    engine = db_engine()
    query = f"SELECT * FROM timeseries_data WHERE series_id = {series_id};"
    df = pd.read_sql(query, engine, params={"series_id" : series_id})
    return df



if __name__ == "__main__":
    print(load_dataframe(2))
