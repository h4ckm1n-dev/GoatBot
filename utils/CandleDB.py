import logging
import os
import time
from datetime import datetime
from binance.client import Client
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables from .env file
load_dotenv()

# Configure logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/DataFeed.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

use_testnet = os.getenv('USE_TESTNET') == 'True'
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
interval = os.getenv('INTERVAL')
symbol = os.getenv('SYMBOL')

if use_testnet:
    client = Client(api_key, api_secret, testnet=True)
else:
    client = Client(api_key, api_secret)

# Initialize SQL database
db_uri = os.getenv('DB_URI_CANDLES')
engine = create_engine(db_uri)
conn = engine.connect()


def create_database_and_table():
    try:
        result = conn.execute(text("SELECT datname FROM pg_catalog.pg_database WHERE datname = :db_name"), {'db_name': f"{symbol}_{interval}"})
        exists = bool(result.fetchone())

        # Create database if it doesn't exist
        if not exists:
            # End the current transaction
            conn.execute(text("COMMIT"))
            # Create the database with name symbol_interval
            conn.execute(text(f"CREATE DATABASE {symbol}_{interval}"))

        # Create candles table if it doesn't exist
        result = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'candles')"))
        exists = bool(result.fetchone()[0])

        if not exists:
            conn.execute(text(f"""
                CREATE TABLE {symbol}_{interval}_candles (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    interval VARCHAR(20) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    open_price NUMERIC(18, 8) NOT NULL,
                    high_price NUMERIC(18, 8) NOT NULL,
                    low_price NUMERIC(18, 8) NOT NULL,
                    close_price NUMERIC(18, 8) NOT NULL,
                    volume NUMERIC(18, 8) NOT NULL
                )
            """))

            conn.execute(text("COMMIT"))
    except Exception as e:
        logger.error("Error:", e)
        
def fetch_and_save_data():
    result = conn.execute(text(f"SELECT MAX(timestamp) FROM {symbol}_{interval}_candles"))
    latest_timestamp = result.fetchone()[0]

    if latest_timestamp:
        start_time = int(latest_timestamp.timestamp() * 1000) + 60_000
    else:
        start_time = client._get_earliest_valid_timestamp(symbol, interval)

    end_time = int(time.time() * 1000)

    while True:
        candles = client.get_historical_klines(symbol, interval, start_time, end_time)

        if not candles:
            logger.info("No new candles to fetch. Waiting for 1m before trying again...")
            time.sleep(60)
            continue

        for candle in candles:
            timestamp = datetime.fromtimestamp(candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            open_price = float(candle[1])
            high_price = float(candle[2])
            low_price = float(candle[3])
            close_price = float(candle[4])
            volume = float(candle[5])

            conn.execute(text(f"INSERT INTO {symbol}_{interval}_candles (symbol, interval, timestamp, open_price, high_price, low_price, close_price, volume) VALUES (:symbol, :interval, :timestamp, :open_price, :high_price, :low_price, :close_price, :volume) ON CONFLICT DO NOTHING"), {
                "symbol": symbol,
                "interval": interval,
                "timestamp": timestamp,
                "open_price": open_price,
                "high_price": high_price,
                "low_price": low_price,
                "close_price": close_price,
                "volume": volume
            })

            conn.execute(text("COMMIT"))

        start_time = int(candles[-1][0]) + 60_000
        logger.info(f"Downloaded {len(candles)} new candles. Last timestamp: {timestamp}")

        logger.debug("Waiting for 60 seconds before fetching the next batch of candles...")
        time.sleep(60)

if __name__ == "__main__":
    create_database_and_table()
    fetch_and_save_data()