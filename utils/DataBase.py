import os
import logging
import time
from sqlalchemy import create_engine, Table, Column, Integer, String, Float, MetaData, text, BigInteger
from binance.client import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Binance client
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
api_testnet_key = os.getenv('BINANCE_TESTNET_KEY')
api_testnet_secret = os.getenv('BINANCE_TESTNET_SECRET')
use_testnet = os.getenv('USE_TESTNET') == 'True'
symbol = os.getenv('SYMBOL')

if use_testnet:
    client = Client(api_testnet_key, api_testnet_secret, testnet=True)
else:
    client = Client(api_key, api_secret)

# Configure logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/DataBase.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize SQL database
db_uri = os.getenv('DB_URI_TRADE')
engine = create_engine(db_uri)

# Check if database exists
conn = engine.connect()
result = conn.execute(text("SELECT datname FROM pg_catalog.pg_database WHERE datname = 'tradingdb'"))
exists = bool(result.fetchone())

# Create database if it doesn't exist
if not exists:
    conn.execute("CREATE DATABASE tradingdb")

# Commit the transaction
conn.execute(text("commit"))


metadata = MetaData()

trades = Table('trades', metadata,
    Column('id', Integer, primary_key=True),
    Column('symbol', String),
    Column('price', Float),
    Column('quantity', Float),
    Column('buy_or_sell', String),
    Column('fee', Float),
    Column('time', BigInteger)
)

metadata.create_all(engine)

def insert_trade(conn, symbol, trade):
    try:
        trade_id = int(trade['id'])
        # Check if trade with the given id already exists in the database
        result = conn.execute(text("SELECT id FROM trades WHERE id = :id"), {'id': trade_id})
        if result.fetchone() is not None:
            # Trade already exists, skip insertion
            return
        price = float(trade['price'])
        quantity = float(trade['qty'])
        time = int(trade['time'])
        is_buyer = trade['buyer']
        fee = float(trade['commission'])

        # Insert the trade into the SQL database              
        ins = trades.insert().values(id=trade_id, symbol=symbol, price=price, quantity=quantity, buy_or_sell='BUY' if is_buyer else 'SELL', fee=fee, time=time)
        conn.execute(ins)

        logging.info(f"Trade for {symbol} - price: {price}, quantity: {quantity}, buy or sell: {'BUY' if is_buyer else 'SELL'}, fee: {fee}, time: {time}")

    except Exception as e:
        logging.error(f"Error inserting trade: {e}")


if __name__ == '__main__':
    latest_trade_id = 0
    while True:
        try:
            # Get trades for BTCUSDT futures
            fetched_trades = []
            from_id = latest_trade_id + 1  # Only fetch trades with ID greater than the latest trade ID
            limit = 1000
            while True:
                temp_trades = client.futures_account_trades(symbol=symbol, fromId=from_id, limit=limit)
                if not temp_trades:
                    break
                fetched_trades += temp_trades
                from_id = fetched_trades[-1]['id'] + 1

            if fetched_trades:
                # Insert the new trades into the SQL database
                new_trades = [trade for trade in fetched_trades if trade['id'] > latest_trade_id]
                for trade in new_trades:
                    insert_trade(conn, symbol, trade)
                latest_trade_id = new_trades[-1]['id']

            else:
                logging.warning("No trades found")

            time.sleep(300)

        except Exception as e:
            logging.error(f"Error: {e}")