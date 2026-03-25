from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine

# --- CONFIG ---
TICKERS = ["UBS", "^GSPC"]
DAYS_BACK = 21  # ~3 weeks
TABLE_NAME = "prices"

DB_URI = "postgresql://quant_user:strong_password@localhost:5432/options_db"


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
    df.to_sql(
        TABLE_NAME,
        engine,
        if_exists="append",
        index=False
    )


def main():
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=DAYS_BACK)

    raw = fetch_data(TICKERS, start_date, end_date)
    df = transform_data(raw)

    engine = create_engine(DB_URI)
    load_to_postgres(df, engine)

    print("Ingestion complete.")


if __name__ == "__main__":
    main()