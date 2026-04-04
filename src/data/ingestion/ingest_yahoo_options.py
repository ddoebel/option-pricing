from datetime import datetime, timezone

import pandas as pd
import yfinance as yf
from sqlalchemy import text

from src.data.ingestion.config import PIPELINE_CONFIG, get_db_config
from db_connect import db_engine


def build_db_url() -> str:
    cfg = get_db_config()
    return (
        f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    )


def to_python_number(value):
    """Convert pandas/numpy values to plain Python values or None."""
    if pd.isna(value):
        return None
    return value


def compute_mid(bid, ask):
    bid = to_python_number(bid)
    ask = to_python_number(ask)

    if bid is None or ask is None:
        return None
    try:
        return float((bid + ask) / 2.0)
    except Exception:
        return None


def infer_option_style(symbol: str) -> str:
    """
    Very rough default convention:
    - US equities / ETFs from Yahoo are usually American style
    """
    # TODO: If later you ingest index options like SPX, adapt this logic.
    return "american"


def get_or_create_underlying(conn, symbol: str) -> int:
    query_insert = text("""
                        INSERT INTO underlyings (symbol, exchange, currency)
                        VALUES (:symbol, :exchange, :currency)
                            ON CONFLICT (symbol) DO NOTHING
                        """)

    query_select = text("""
                        SELECT id FROM underlyings WHERE symbol = :symbol
                        """)

    # TODO: improve exchange/currency detection if you want richer metadata
    conn.execute(query_insert, {
        "symbol": symbol,
        "exchange": None,
        "currency": "USD",
    })

    result = conn.execute(query_select, {"symbol": symbol}).fetchone()
    return result[0] #h


def get_or_create_contract(
        conn,
        underlying_id: int,
        option_type: str,
        strike: float,
        expiration_date,
        style: str,
        contract_symbol: str,
) -> int:
    query_insert = text("""
                        INSERT INTO option_contracts (
                            underlying_id, option_type, strike, expiration_date, style, contract_symbol
                        )
                        VALUES (
                                   :underlying_id, :option_type, :strike, :expiration_date, :style, :contract_symbol
                               )
                            ON CONFLICT (underlying_id, option_type, strike, expiration_date)
        DO NOTHING
                        """)

    query_select = text("""
                        SELECT id
                        FROM option_contracts
                        WHERE underlying_id = :underlying_id
                          AND option_type = :option_type
                          AND strike = :strike
                          AND expiration_date = :expiration_date
                        """)

    conn.execute(query_insert, {
        "underlying_id": underlying_id,
        "option_type": option_type,
        "strike": strike,
        "expiration_date": expiration_date,
        "style": style,
        "contract_symbol": contract_symbol,
    })

    result = conn.execute(query_select, {
        "underlying_id": underlying_id,
        "option_type": option_type,
        "strike": strike,
        "expiration_date": expiration_date,
    }).fetchone()

    return result[0]


def insert_underlying_price(conn, underlying_id: int, timestamp: datetime, price: float):
    query = text("""
                 INSERT INTO underlying_prices (underlying_id, timestamp, price)
                 VALUES (:underlying_id, :timestamp, :price)
                     ON CONFLICT (underlying_id, timestamp) DO NOTHING
                 """)
    conn.execute(query, {
        "underlying_id": underlying_id,
        "timestamp": timestamp,
        "price": price,
    })


def insert_option_quote(
        conn,
        contract_id: int,
        timestamp: datetime,
        bid,
        ask,
        mid,
        last_price,
        implied_vol,
        volume,
        open_interest,
):
    query = text("""
                 INSERT INTO option_quotes (
                     contract_id, timestamp, bid, ask, mid,
                     last_price, implied_vol, volume, open_interest
                 )
                 VALUES (
                            :contract_id, :timestamp, :bid, :ask, :mid,
                            :last_price, :implied_vol, :volume, :open_interest
                        )
                     ON CONFLICT (contract_id, timestamp) DO NOTHING
                 """)

    conn.execute(query, {
        "contract_id": contract_id,
        "timestamp": timestamp,
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "last_price": last_price,
        "implied_vol": implied_vol,
        "volume": volume,
        "open_interest": open_interest,
    })


def process_option_dataframe(conn, df: pd.DataFrame, underlying_id: int, option_type: str, symbol: str, expiration_date, timestamp: datetime):
    style = infer_option_style(symbol)

    for _, row in df.iterrows():
        strike = to_python_number(row.get("strike"))
        contract_symbol = to_python_number(row.get("contractSymbol"))
        bid = to_python_number(row.get("bid"))
        ask = to_python_number(row.get("ask"))
        last_price = to_python_number(row.get("lastPrice"))
        implied_vol = to_python_number(row.get("impliedVolatility"))
        volume = to_python_number(row.get("volume"))
        open_interest = to_python_number(row.get("openInterest"))

        if strike is None:
            continue

        contract_id = get_or_create_contract(
            conn=conn,
            underlying_id=underlying_id,
            option_type=option_type,
            strike=float(strike),
            expiration_date=expiration_date,
            style=style,
            contract_symbol=contract_symbol,
        )

        mid = compute_mid(bid, ask)

        insert_option_quote(
            conn=conn,
            contract_id=contract_id,
            timestamp=timestamp,
            bid=bid,
            ask=ask,
            mid=mid,
            last_price=last_price,
            implied_vol=implied_vol,
            volume=int(volume) if volume is not None else None,
            open_interest=int(open_interest) if open_interest is not None else None,
        )


def ingest_symbol(symbol: str, engine):
    print(f"Starting ingestion for {symbol}...")

    ticker = yf.Ticker(symbol)
    expirations = ticker.options

    if not expirations:
        print(f"No options found for {symbol}")
        return

    timestamp = datetime.now(timezone.utc)

    # Try to get spot price
    info = {}
    try:
        info = ticker.fast_info
    except Exception:
        pass

    spot_price = None
    if info:
        spot_price = info.get("lastPrice") or info.get("last_price")

    with engine.begin() as conn:
        underlying_id = get_or_create_underlying(conn, symbol)

        if spot_price is not None:
            insert_underlying_price(
                conn=conn,
                underlying_id=underlying_id,
                timestamp=timestamp,
                price=float(spot_price),
            )

        for expiry in expirations:
            print(f"  Fetching expiry {expiry} ...")
            chain = ticker.option_chain(expiry)

            expiration_date = pd.to_datetime(expiry).date()

            process_option_dataframe(
                conn=conn,
                df=chain.calls,
                underlying_id=underlying_id,
                option_type="call",
                symbol=symbol,
                expiration_date=expiration_date,
                timestamp=timestamp,
            )

            process_option_dataframe(
                conn=conn,
                df=chain.puts,
                underlying_id=underlying_id,
                option_type="put",
                symbol=symbol,
                expiration_date=expiration_date,
                timestamp=timestamp,
            )

    print(f"Finished ingestion for {symbol}.")


def main():
    engine = db_engine()

    for symbol in PIPELINE_CONFIG["symbols"]:
        ingest_symbol(symbol, engine)


if __name__ == "__main__":
    main()