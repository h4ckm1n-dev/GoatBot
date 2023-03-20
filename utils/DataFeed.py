import os
import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
import backtrader as bt
from dotenv import load_dotenv

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

interval = os.getenv('INTERVAL')
symbol = os.getenv('SYMBOL')

# Default start and end dates
start_date = os.getenv('START_DATE')
end_date = os.getenv('END_DATE')

# Initialize SQL database
db_uri = os.getenv('DB_URI_CANDLES')
engine = create_engine(db_uri)

class BinanceData(bt.feeds.PandasData):
    """Custom Data Feed for Binance data."""
    lines = ('open', 'high', 'low', 'close', 'volume')

    params = (
        ('nocase', True),
        ('datetime', 0),
        ('open', 1),
        ('high', 2),
        ('low', 3),
        ('close', 4),
        ('volume', 5),
        ('openinterest', -1)
    )

    @classmethod
    def from_database(cls, symbol, interval, start_date, end_date, limit=10000):
        """Fetch Binance data from the database and return a DataFrame."""
        try:
            sql = text(f"SELECT * FROM {symbol}_{interval}_candles WHERE timestamp >= '{start_date}' AND timestamp <= '{end_date}' ORDER BY timestamp DESC LIMIT {limit}")
            with engine.connect() as connection:
                df = pd.read_sql_query(sql, connection)
            return df
        except Exception as e:
            logger.error(f"Error fetching data from the database: {e}")
            raise

if __name__ == '__main__':
    try:
        symbol = os.getenv('SYMBOL')
        interval = os.getenv('INTERVAL')
        start_date = os.getenv('START_DATE')
        end_date = os.getenv('END_DATE')

        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')

        # Data Feeds
        data = BinanceData.from_database(symbol, interval, start_date, end_date)
        logger.info(f"Created data feed object for {symbol} {interval} data from {start_date} to {end_date}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise
