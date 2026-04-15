from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

from db_connect import db_engine
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import MetaData, Table

# --- CONFIG ---
TICKERS = ["UBS", "^GSPC"]
DAYS_BACK = 31  # ~3 weeks
TABLE_NAME = "prices"

def fetch_data(tickers, start_date, end_date):
    data = yf.download(
        tickers,
        start=start_date,
        end=end_date,
        group_by="ticker",
        auto_adjust=True,
        progress=False
    )
    return data

def get_asset_map(engine): 
    query = "SELECT id, ticker FROM assets"
    df = pd.read_sql(query, engine)
    return dict(zip(df["ticker"], df["id"]))


def transform_data(raw_data):
    frames = []

    for ticker in raw_data.columns.levels[0]:
        df = raw_data[ticker].copy()
        df["ticker"] = ticker
        df = df.reset_index()

        # Keep only what we need
        df = df[["Date", "ticker", "Close", "Volume"]]

        df.rename(columns={
            "Date": "date",
            "Close": "close",
            "Volume": "volume"
        }, inplace=True)

        # Compute daily returns
        df["return"] = df["close"].pct_change()

        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def load_to_postgres(df, engine):
    asset_map = get_asset_map(engine)
    df["asset_id"] = df["ticker"].map(asset_map)
    df = df.drop(columns=["ticker"])

    metadata = MetaData()
    prices = Table(TABLE_NAME, metadata, autoload_with=engine)

    with engine.begin() as conn:
        for _, row in df.iterrows():
            stmt = insert(prices).values({
                "asset_id": row["asset_id"],
                "date": row["date"],
                "close": row["close"],
                "volume": row["volume"],
                "return": row["return"]
            })

            stmt = stmt.on_conflict_do_update(
            index_elements=["asset_id", "date"],
            set_={
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "return": stmt.excluded["return"],  # important change
            }
        )

            conn.execute(stmt)


def main():
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=DAYS_BACK)

    raw = fetch_data(TICKERS, start_date, end_date)
    df = transform_data(raw)

    engine = db_engine()
    load_to_postgres(df, engine)

    print("Ingestion complete.")


if __name__ == "__main__":
    main()