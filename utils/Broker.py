import os
import logging
from dotenv import load_dotenv
from binance_f import RequestClient
from binance_f import RequestClient
from binance_f.model import OrderSide, OrderType

# Load environment variables
load_dotenv()

# Configure logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/broker.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

symbol = os.getenv('SYMBOL')
use_testnet = os.getenv('USE_TESTNET') == 'True'
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
api_testnet_key = os.getenv('BINANCE_TESTNET_KEY')
api_testnet_secret = os.getenv('BINANCE_TESTNET_SECRET')
if use_testnet:
    api_key = os.getenv('BINANCE_TESTNET_KEY')
    api_secret = os.getenv('BINANCE_TESTNET_SECRET')
    api_url = 'https://testnet.binancefuture.com'
else:
    api_url = 'https://fapi.binance.com'
    symbol += '_PERP'
    
# Backtrader Setting
sec_type = os.getenv('MARKET_TYPE')
leverage = int(os.getenv('LEVERAGE'))
margin_type = os.getenv('MARGIN_TYPE')

class BinanceBroker:
    def __init__(self, api_key, api_secret, use_testnet, symbol, margin_type, leverage):
        self.client = RequestClient(api_key=api_key, secret_key=api_secret, url=api_url)
        self.symbol = symbol
        self.margin_type = margin_type
        self.set_leverage(leverage) 

    def buy(self, quantity):
        try:
            quantity = float(quantity)
        except ValueError:
            print("Invalid quantity. Quantity must be a number.")
            return None

        if quantity <= 0:
            print("Invalid quantity. Quantity must be greater than 0.")
            return None

        try:
            order = self.client.post_order(symbol=self.symbol, side=OrderSide.BUY, ordertype=OrderType.MARKET, quantity=quantity)
            return order
        except Exception as e:
            print(f"Error buying {quantity} {self.symbol}: {e}")
            return None

    def sell(self, quantity):
        try:
            quantity = float(quantity)
        except ValueError:
            print("Invalid quantity. Quantity must be a number.")
            return None

        if quantity <= 0:
            print("Invalid quantity. Quantity must be greater than 0.")
            return None

        try:
            order = self.client.post_order(symbol=self.symbol, side=OrderSide.SELL, ordertype=OrderType.MARKET, quantity=quantity)
            return order
        except Exception as e:
            print(f"Error selling {quantity} {self.symbol}: {e}")
            return None

    def get_balance_broker(self):
        try:
            balance = self.client.get_balance()
            assets = []
            for b in balance:
                assets.append(b.asset)
            return assets
        except Exception as e:
            print(f"Error getting balance: {e}")
            return None

    def set_leverage(self, leverage):
        try:
            self.client.change_initial_leverage(symbol=self.symbol, leverage=leverage)
        except Exception as e:
            print(f"Error setting leverage for {self.symbol}: {e}")

    def set_commission(self, maker_rate, taker_rate):
        try:
            exchange_info = self.client.get_exchange_information()
            symbol_filters = [s for s in exchange_info.symbols if s.symbol == self.symbol][0].filters
            for f in symbol_filters:
                if hasattr(f, 'filterType') and f.filterType == 'COMMISSION_RATE':
                    maker_rate = float(f.makerCommissionRate)
                    taker_rate = float(f.takerCommissionRate)
                    break
            self.client.change_trade_fee(symbol=self.symbol, makerCommission=maker_rate, takerCommission=taker_rate)
        except Exception as e:
            print(f"Error setting commission rate for {self.symbol}: {e}")

if __name__ == "__main__":
    broker = BinanceBroker(api_key, api_secret, use_testnet, symbol, margin_type, leverage)
    balance = broker.get_balance_broker()
    print(balance)

