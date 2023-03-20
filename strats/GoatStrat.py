import backtrader as bt
import os
import logging
from binance.client import Client
from dotenv import load_dotenv
from utils.Broker import BinanceBroker
from utils.Risk import position_size, RISK_PERCENTAGE, ACCOUNT_SIZE

# Load environment variables
load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
api_testnet_key = os.getenv('BINANCE_TESTNET_KEY')
api_testnet_secret = os.getenv('BINANCE_TESTNET_SECRET')
use_testnet = os.getenv('USE_TESTNET') == 'True'

# Configure logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/GoatBot.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class GoatStrat(bt.Strategy):
    params = dict(
        binance_api_key = os.getenv('BINANCE_API_KEY'),
        binance_api_secret = os.getenv('BINANCE_API_SECRET'),
        binance_testnet_key = os.getenv('BINANCE_TESTNET_KEY'),
        binance_testnet_secret = os.getenv('BINANCE_TESTNET_SECRET'),
        use_testnet = os.getenv('USE_TESTNET') == 'True',
        api_url = 'https://testnet.binancefuture.com/fapi/v1' if use_testnet else 'https://fapi.binance.com/fapi/v1',
        bb_length = int(os.getenv("BB_LENGTH")),
        mult = float(os.getenv("MULT")),
        trailing_stop = float(os.getenv("TRAILING_STOP")),
        profit_target = float(os.getenv("PROFIT_TARGET")),
        rsi_period = int(os.getenv("RSI_PERIOD")),
        vol_period = int(os.getenv("VOL_PERIOD")),
        entry_rsi = float(os.getenv("ENTRY_RSI")),
        exit_rsi = float(os.getenv("EXIT_RSI")),
        entry_vol = float(os.getenv("ENTRY_VOL")),
        exit_vol = float(os.getenv("EXIT_VOL")),
        max_trade_percentage = float(os.getenv("MAX_TRADE_PERCENTAGE")),
        pyramid_num = int(os.getenv('PYRAMID_NUM')),
        pyramid_size_ratio = float(os.getenv('PYRAMID_SIZE_RATIO')),
        sec_type = os.getenv('MARKET_TYPE'),
        exchange = os.getenv('EXCHANGE'),
        leverage = int(os.getenv('LEVERAGE')),
        margin_type = os.getenv('MARGIN_TYPE'),
    )

    def __init__(self):
        self.binance_api_key = self.params.binance_api_key
        self.binance_api_secret = self.params.binance_api_secret
        self.binance_testnet_key = self.params.binance_testnet_key
        self.binance_testnet_secret = self.params.binance_testnet_secret
        self.use_testnet = self.params.use_testnet
        self.bb_length = self.params.bb_length
        self.mult = self.params.mult
        self.trailing_stop = self.params.trailing_stop
        self.profit_target = self.params.profit_target
        self.rsi_period = self.params.rsi_period
        self.vol_period = self.params.vol_period
        self.entry_rsi = self.params.entry_rsi
        self.exit_rsi = self.params.exit_rsi
        self.entry_vol = self.params.entry_vol
        self.exit_vol = self.params.exit_vol
        self.max_trade_percentage = self.params.max_trade_percentage
        self.pyramid_num = self.params.pyramid_num
        self.pyramid_size_ratio = self.params.pyramid_size_ratio
        self.sec_type = self.params.sec_type
        self.exchange = self.params.exchange
        self.leverage = self.params.leverage
        self.margin_type = self.params.margin_type
        self.basis = bt.indicators.SimpleMovingAverage(self.data.close, period=self.bb_length)
        self.dev = self.mult * bt.indicators.StdDev(self.data.close, period=self.bb_length)
        self.upper1 = self.basis + self.dev
        self.lower1 = self.basis - self.dev
        self.rsi = bt.indicators.RSI_EMA(self.data.close, period=self.rsi_period)
        self.vol = self.data.volume

        if self.use_testnet:
            self.client = Client(self.binance_testnet_key, self.binance_testnet_secret, testnet=True)
        else:
            self.client = Client(self.binance_api_key, self.binance_api_secret)

    def next(self):
        # Get current cash balance
        cash = self.broker.get_cash()
        if cash == 0:
            return

        price = self.data.close[0]
        stop_loss = price * (1 - self.params.stop_loss)
        take_profit = price * (1 + self.params.take_profit)

        potential_loss = price - stop_loss
        trade_size = position_size(potential_loss, RISK_PERCENTAGE, ACCOUNT_SIZE)
        
        # Calculate trade size based on max_trade_percentage
        max_trade_percentage = self.params.max_trade_percentage
        price = self.data.close[0]
        size = (max_trade_percentage / 100) * cash / price

        # Calculate additional trade sizes based on pyramid_num and pyramid_size_ratio
        total_size = size
        for i in range(1, self.pyramid_num + 1):
            pyr_size = total_size * self.pyramid_size_ratio
            if pyr_size > 0:
                logger.debug(f"Adding pyramid position {i} of size {pyr_size:.2f}")
                if self.position.size > 0:
                    self.buy(size=pyr_size)
                elif self.position.size < 0:
                    self.sell(size=pyr_size)
                total_size += pyr_size

        # Enter long or short trade based on the entry conditions
        if self.position.size == 0:
            if self.data.close[0] > self.upper1[0] and self.rsi[0] > self.entry_rsi and self.vol[0] > self.entry_vol * bt.indicators.SMA(self.vol, period=self.vol_period)[0]:
                logger.debug(f"Entering long trade of size {trade_size:.2f}")
                self.buy(size=trade_size)
                self.params.stop_loss = stop_loss
                self.params.take_profit = take_profit
            elif self.data.close[0] < self.lower1[0] and self.rsi[0] < self.entry_rsi and self.vol[0] > self.entry_vol * bt.indicators.SMA(self.vol, period=self.vol_period)[0]:
                logger.debug(f"Entering short trade of size {trade_size:.2f}")
                self.sell(size=trade_size)
                self.params.stop_loss = stop_loss
                self.params.take_profit = take_profit
                
        # Define the trailing stop and profit target price levels
        long_trailing_stop = self.data.close[0] - self.trailing_stop / 100 * self.dev[0]
        long_profit_target = self.data.close[0] + self.profit_target / 100 * self.dev[0]
        short_trailing_stop = self.data.close[0] + self.trailing_stop / 100 * self.dev[0]
        short_profit_target = self.data.close[0] - self.profit_target / 100 * self.dev[0]       

        # Define exit conditions for long and short positions
        long_exit_condition = (
            self.data.close[0] < long_trailing_stop
            or self.data.close[0] > long_profit_target
            or self.rsi[0] < self.exit_rsi
            or self.vol[0] < self.exit_vol * bt.indicators.SMA(self.vol, period=self.vol_period)[0]
        )
        short_exit_condition = (
            self.data.close[0] > short_trailing_stop
            or self.data.close[0] < short_profit_target
            or self.rsi[0] > 100 - self.exit_rsi
            or self.vol[0] < self.exit_vol * bt.indicators.SMA(self.vol, period=self.vol_period)[0]
        )       

        # Exit long or short positions based on the exit conditions
        if self.position.size > 0 and long_exit_condition:
            logger.debug("Exiting long trade")
            self.close()
        elif self.position.size < 0 and short_exit_condition:
            logger.debug("Exiting short trade")
            self.close()        

    @staticmethod
    def getbroker():
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        use_testnet = os.getenv('USE_TESTNET') == 'True'
        broker = BinanceBroker(api_key=api_key, api_secret=api_secret, use_testnet=use_testnet)
        return broker