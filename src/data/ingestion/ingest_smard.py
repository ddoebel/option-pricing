import argparse

import pandas as pd
import requests
from sqlalchemy import text

from src.data.ingestion.db_connect import db_engine

SMARD_SOURCE = "SMARD"
SMARD_FILTER_ID = 4169
SMARD_REGION = "DE"
SMARD_RESOLUTION = "hour"


class SmardLoader:
    BASE_URL = "https://www.smard.de/app/chart_data"

    def __init__(self, filter_id=SMARD_FILTER_ID, region=SMARD_REGION, resolution=SMARD_RESOLUTION):
        self.filter_id = filter_id
        self.region = region
        self.resolution = resolution

    def fetch_available_timestamps(self) -> pd.DataFrame:
        url = f"{self.BASE_URL}/{self.filter_id}/{self.region}/index_{self.resolution}.json"
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        data = r.json()

        df = pd.DataFrame(data["timestamps"], columns=["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Convert to datetime (UTC → Zurich)
        df["timestamp_datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df["timestamp_datetime"] = df["timestamp_datetime"].dt.tz_convert("Europe/Zurich")

        return df

    def fetch_timestamp(self, timestamp: int) -> pd.DataFrame:
        url = (
            f"{self.BASE_URL}/{self.filter_id}/{self.region}/"
            f"{self.filter_id}_{self.region}_{self.resolution}_{timestamp}.json"
        )

        r = requests.get(url, timeout=120)
        r.raise_for_status()
        data = r.json()

        df = pd.DataFrame(data["series"], columns=["timestamp", "price"])

        # Convert timestamp (UTC → Zurich)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df["timestamp"] = df["timestamp"].dt.tz_convert("Europe/Zurich")

        # Clean
        df = df.dropna().sort_values("timestamp").reset_index(drop=True)

        return df

    def fetch_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch data for calendar dates start_date through end_date (inclusive full days,
        Europe/Zurich).
        Example: "2023-01-01", "2023-01-03" → 1 Jan–3 Jan inclusive.
        """

        start = pd.Timestamp(start_date).tz_localize("Europe/Zurich")
        end_exclusive = pd.Timestamp(end_date).tz_localize("Europe/Zurich") + pd.Timedelta(days=1)

        timestamps_df = self.fetch_available_timestamps()

        # Weekly index blocks: keep any block that might overlap [start, end_exclusive)
        relevant = timestamps_df[
            (timestamps_df["timestamp_datetime"] >= start - pd.Timedelta(days=7))
            & (timestamps_df["timestamp_datetime"] < end_exclusive + pd.Timedelta(days=7))
        ]

        dfs = []

        for ts in relevant["timestamp"]:
            print(f"Fetching block {ts}...")
            df = self.fetch_timestamp(ts)
            dfs.append(df)

        if not dfs:
            return pd.DataFrame(columns=["timestamp", "price"])

        full_df = pd.concat(dfs).drop_duplicates().reset_index(drop=True)

        full_df = full_df[
            (full_df["timestamp"] >= start)
            & (full_df["timestamp"] < end_exclusive)
        ]

        return full_df


def ensure_smard_series_metadata(engine) -> int:
    """Insert SMARD series row if missing; return its id (matches schema + loader defaults)."""
    upsert = text(
        """
        INSERT INTO series_metadata
            (name, region, unit, source, filter_id, category, subcategory, resolution)
        VALUES
            ('ElectricityPrice', :region, 'EUR/MWh', :source, :filter_id,
             'price', 'day_ahead', :resolution)
        ON CONFLICT (source, filter_id, region, resolution) DO NOTHING
        """
    )
    sel = text(
        """
        SELECT id FROM series_metadata
        WHERE source = :source
          AND filter_id = :filter_id
          AND region = :region
          AND resolution = :resolution
        """
    )
    params = {
        "source": SMARD_SOURCE,
        "filter_id": SMARD_FILTER_ID,
        "region": SMARD_REGION,
        "resolution": SMARD_RESOLUTION,
    }
    with engine.begin() as conn:
        conn.execute(upsert, params)
        row = conn.execute(sel, params).fetchone()
    if row is None:
        raise RuntimeError("Could not resolve series_metadata id for SMARD DE hourly series")
    return int(row[0])


def save_to_postgres(df: pd.DataFrame, series_id: int, engine) -> None:
    """Append hourly rows; skips duplicates on (series_id, timestamp)."""
    if df.empty:
        return

    out = df.rename(columns={"price": "value"}).copy()
    out["series_id"] = series_id

    records = out[["timestamp", "value", "series_id"]].to_dict("records")
    stmt = text(
        """
        INSERT INTO timeseries_data ("timestamp", value, series_id)
        VALUES (:timestamp, :value, :series_id)
        ON CONFLICT (series_id, "timestamp") DO NOTHING
        """
    )
    with engine.begin() as conn:
        conn.execute(stmt, records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest SMARD electricity prices into PostgreSQL.")
    parser.add_argument(
        "--fetch-only",
        action="store_true",
        help="Only download and print data; do not connect to the database.",
    )
    parser.add_argument(
        "--start",
        default="2023-01-01",
        help="Start date (YYYY-MM-DD), Europe/Zurich.",
    )
    parser.add_argument(
        "--end",
        default="2023-01-03",
        help="End date (YYYY-MM-DD), inclusive, Europe/Zurich.",
    )
    args = parser.parse_args()

    loader = SmardLoader()
    df = loader.fetch_date_range(args.start, args.end)

    print(df.head())
    print(df.tail())
    print(f"\nTotal rows: {len(df)}")

    if args.fetch_only:
        raise SystemExit(0)

    eng = db_engine()
    sid = ensure_smard_series_metadata(eng)
    save_to_postgres(df, sid, eng)
    print(f"Saved to PostgreSQL (series_id={sid}).")
