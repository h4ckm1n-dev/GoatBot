import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
import backtrader as bt
from backtrader.analyzers import SharpeRatio, DrawDown, TimeReturn, TradeAnalyzer
from dotenv import load_dotenv
from strats.GoatStrat import GoatStrat

# Load environment variables from .env file
load_dotenv()

# Configure logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs/BackTest.log')
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
db_uri = os.getenv('DB_URI_CANDLES')
engine = create_engine(db_uri)

class BinanceData(bt.feeds.PandasData):
    """Custom Data Feed for Binance data."""
    lines = ('open', 'high', 'low', 'close', 'volume')

    params = (
        ('nocase', True),
        ('datetime', 3),
        ('open', 4),
        ('high', 5),
        ('low', 6),
        ('close', 7),
        ('volume', 8),
        ('openinterest', -1)
    )

    @classmethod
    def from_database(cls, symbol, interval, start_date, end_date, limit=10000):
        """Fetch Binance data from the database and return a DataFrame."""
        sql = text(f"SELECT * FROM {symbol}_{interval}_candles WHERE timestamp >= '{start_date}' AND timestamp <= '{end_date}' ORDER BY timestamp DESC LIMIT {limit}")
        with engine.connect() as connection:
            df = pd.read_sql_query(sql, connection)

        # Convert columns with Timestamp objects to float values
        df['open'] = pd.to_numeric(df['open_price'])
        df['high'] = pd.to_numeric(df['high_price'])
        df['low'] = pd.to_numeric(df['low_price'])
        df['close'] = pd.to_numeric(df['close_price'])
        df['volume'] = pd.to_numeric(df['volume'])

        return cls(dataname=df)

def run_backtest(symbol, interval, start_date, end_date):
    """Run the backtest and return the results."""
    # Data Feeds
    data = BinanceData.from_database(symbol, interval, start_date, end_date)
    logger.info(f"Created data feed object for {symbol} {interval} data from {start_date} to {end_date}")

    # Cerebro
    cerebro = bt.Cerebro()
    cerebro.addstrategy(GoatStrat)

    # Add data to Cerebro
    cerebro.adddata(data)

    # Set the cash balance for the backtest
    cerebro.broker.setcash(1000)

    # Set the commission scheme
    cerebro.broker.setcommission(commission=0.001)

    # Add analyzers to Cerebro
    cerebro.addanalyzer(SharpeRatio)
    cerebro.addanalyzer(DrawDown)
    cerebro.addanalyzer(TimeReturn)
    cerebro.addanalyzer(TradeAnalyzer)

    # Run the backtest and return the results
    return cerebro.run()

def analyze_results(results):
    """Analyze the results and log the output."""
    # Get the analyzers from the results
    sharpe_ratio = results[0].analyzers.sharperatio.get_analysis()
    drawdown = results[0].analyzers.drawdown.get_analysis()
    time_return = results[0].analyzers.timereturn.get_analysis()
    trade_analyzer = results[0].analyzers.tradeanalyzer.get_analysis()

    # Log the results
    logger.info(f"Sharpe Ratio: {sharpe_ratio['sharperatio']:.2f}")
    logger.info(f"Max Drawdown: {drawdown['max']['drawdown']:.2%}")
    logger.info(f"Total Return: {time_return['timereturn']:.2%}")
    logger.info(f"Total Trades: {trade_analyzer['total']['total']}")
    logger.info(f"Total Wins: {trade_analyzer['won']['total']}")
    logger.info(f"Total Losses: {trade_analyzer['lost']['total']}")
    logger.info(f"Win Rate: {trade_analyzer['won']['total'] / trade_analyzer['total']['total']:.2%}")

if __name__ == '__main__':
    try:
        symbol = os.getenv('SYMBOL')
        interval = os.getenv('INTERVAL')
        start_date = pd.to_datetime(os.getenv('START_DATE'))
        end_date = pd.to_datetime(os.getenv('END_DATE'))

        # Run the backtest
        results = run_backtest(symbol, interval, start_date, end_date)

        # Analyze and log the results
        analyze_results(results)

        # Plot the results
        bt.Cerebro().plot()

    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        raise e
