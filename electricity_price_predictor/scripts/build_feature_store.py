import argparse
import os

import pandas as pd

from electricity_price_predictor.db import get_engine
from electricity_price_predictor.pipeline import run_feature_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch ENTSO-E inputs and build feature store.")
    parser.add_argument("--country-code", required=True, help="ENTSO-E bidding zone code, e.g. DE_LU")
    parser.add_argument("--start", required=True, help="Inclusive start datetime, e.g. 2026-01-01T00:00:00Z")
    parser.add_argument("--end", required=True, help="Exclusive end datetime, e.g. 2026-02-01T00:00:00Z")
    parser.add_argument("--cache-ttl-hours", type=int, default=24, help="Decorator cache TTL in hours")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = os.getenv("ENTSOE_API_KEY")
    if not api_key:
        raise RuntimeError("ENTSOE_API_KEY environment variable is required.")

    engine = get_engine()
    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC")

    features = run_feature_pipeline(
        engine=engine,
        entsoe_api_key=api_key,
        country_code=args.country_code,
        start=start,
        end=end,
        cache_ttl_hours=args.cache_ttl_hours,
    )
    print(f"Persisted {len(features)} feature rows for {args.country_code}.")


if __name__ == "__main__":
    main()
