import os
import time
import logging
import multiprocessing
import backtrader as bt
from dotenv import load_dotenv
from datetime import datetime, timedelta
from strats.GoatStrat import GoatStrat
from utils.DataBase import insert_trade
from utils.CandleDB import insert_data_to_db
from utils.DataFeed import BinanceData
from utils.Risk import manage_trade, get_margin_percentage
from utils.SafeAPI import safe_api_call
from binance_f import RequestClient
from binance_f.constant.test import *
from binance_f.base.printobject import *
from utils.Broker import BinanceBroker
from utils.Risk import RiskManagement

# Load environment variables
load_dotenv()

# Configure logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs/Main.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Trading Settings
symbol = os.getenv('SYMBOL')
interval = os.getenv('INTERVAL')
use_testnet = os.getenv('USE_TESTNET') == 'True'
backtesting = os.getenv('BACKTESTING') == 'True'
margin_type = os.getenv('MARGIN_TYPE')
leverage = int(os.getenv('LEVERAGE'))
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
api_testnet_key = os.getenv('BINANCE_TESTNET_KEY')
data_pair = os.getenv('DATA_PAIR')

# Default start and end dates
start_date = os.getenv('START_DATE')
end_date = os.getenv('END_DATE')

if use_testnet:
    api_key = os.getenv('BINANCE_TESTNET_KEY')
    api_secret = os.getenv('BINANCE_TESTNET_SECRET')
    api_url = 'https://testnet.binancefuture.com'
else:
    api_url = 'https://fapi.binance.com'
    #symbol += '_PERP'

def get_balance(api_key, api_secret, use_testnet, symbol, margin_type):
    broker = BinanceBroker(api_key=api_key, api_secret=api_secret, use_testnet=use_testnet, symbol=symbol, margin_type=margin_type)
    balance = broker.get_balance_broker()
    usdt_balance = float([asset['balance'] for asset in balance if asset['asset'] == 'USDT'][0])
    logger.info(f"Account balance: ${usdt_balance:.2f}")
    return usdt_balance

# Set commissions and leverage
def set_commissions_and_leverage(broker, margin_type, leverage):
    maker_rate, taker_rate = 0, 0
    broker.set_commission(maker_rate, taker_rate)
    logging.info(f"Setting margin type to {margin_type}")
    logging.info(f"Setting leverage to {leverage} for symbol {broker.symbol}")
    broker.set_leverage(leverage)

if __name__ == '__main__':
    if use_testnet:
        logger.info("Running on Binance Testnet")
        # Set Binance Testnet API keys
        api_key = os.getenv('BINANCE_TESTNET_KEY')
        api_secret = os.getenv('BINANCE_TESTNET_SECRET')
        api_url = 'https://testnet.binancefuture.com'
    else:
        logger.info("Running on Binance Production")
        api_url = 'https://fapi.binance.com'
        #symbol += '_PERP'
        
    data = BinanceData.from_database(symbol, interval, start_date, end_date)
    data = bt.feeds.PandasData(dataname=data)
    logging.info(f"Created data feed object for {symbol} {interval} data for live trading")

    # Create strategy object
    strategy = GoatStrat
    logging.info(f"Created strategy object: {strategy.__name__}")

    # Create a broker object using the BinanceBroker class
    broker = BinanceBroker(api_key=api_key, api_secret=api_secret, use_testnet=use_testnet, symbol=symbol, margin_type=margin_type)
    set_commissions_and_leverage(broker, margin_type, leverage)
    logging.info("Created broker object and set commissions and leverage")

    # Instantiate the RiskManagement class
    risk_management = RiskManagement(
        max_drawdown=float(os.getenv("MAX_DRAWDOWN")),
        max_consecutive_losses=int(os.getenv("MAX_CONSECUTIVE_LOSSES")),
        max_leverage=int(os.getenv("MAX_LEVERAGE")),
    )

    # Initialize strategy with broker, data feed, and risk management
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy, broker=broker, risk_management=risk_management)  # Pass the risk_management object
    cerebro.adddata(data)
    logging.info("Initialized strategy with broker, data feed, and risk management")

    # Add risk management function to strategy
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Transactions, _name='transactions')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    # Start trading loop
    logging.info("Started trading loop")
    while True:
        try:
            cerebro.run()
        except Exception as e:
            logging.error(f"Error running strategy: {e}")
        time.sleep(60) # Sleep for 1 minute before running again. Adjust this if needed.
