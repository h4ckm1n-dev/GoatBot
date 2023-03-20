import os
from dotenv import load_dotenv

load_dotenv()

# Trading Environement
use_testnet = os.getenv('USE_TESTNET') == 'True'

exchange = os.getenv('EXCHANGE')
commission = float(os.getenv('COMMISSION'))
# Binance Setting
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
api_testnet_key = os.getenv('BINANCE_TESTNET_KEY')
api_testnet_secret = os.getenv('BINANCE_TESTNET_SECRET')
symbol = os.getenv('SYMBOL')
data_pair = os.getenv('DATA_PAIR')

# Trading Setting
interval = os.getenv('INTERVAL')
bb_length = int(os.getenv('BB_LENGTH'))
mult = float(os.getenv('MULT'))
trailing_stop = float(os.getenv('TRAILING_STOP'))
profit_target = float(os.getenv('PROFIT_TARGET'))
rsi_period = int(os.getenv('RSI_PERIOD'))
vol_period = int(os.getenv('VOL_PERIOD'))
entry_rsi = float(os.getenv('ENTRY_RSI'))
exit_rsi = float(os.getenv('EXIT_RSI'))
entry_vol = float(os.getenv('ENTRY_VOL'))
exit_vol = float(os.getenv('EXIT_VOL'))
max_trade_percentage = float(os.getenv('MAX_TRADE_PERCENTAGE'))
pyramid_num = int(os.getenv('PYRAMID_NUM'))
pyramid_size_ratio = float(os.getenv('PYRAMID_SIZE_RATIO'))

# Backtrader Setting
sec_type = os.getenv('MARKET_TYPE')
leverage = int(os.getenv('LEVERAGE'))
margin_type = os.getenv('MARGIN_TYPE')

# TradingBot misc
debug_level = os.getenv('DEBUG_LEVEL')
db_uri_trade = os.getenv('DB_URI_TRADE')
db_uri_candles = os.getenv('DB_URI_CANDLES')

# Default start and end dates
start_date = os.getenv('START_DATE')
end_date = os.getenv('END_DATE')