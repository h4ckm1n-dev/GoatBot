import os
import time
import logging
from binance.client import Client
from dotenv import load_dotenv
from binance.enums import *
from binance.exceptions import BinanceAPIException
from .DataBase import insert_trade
from .SafeAPI import safe_api_call

# Load environment variables
load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
api_testnet_key = os.getenv('BINANCE_TESTNET_KEY')
api_testnet_secret = os.getenv('BINANCE_TESTNET_SECRET')
use_testnet = os.getenv('USE_TESTNET') == 'True'
symbol = os.getenv('SYMBOL')

# Initialize Binance client
if use_testnet:
    client = Client(api_testnet_key, api_testnet_secret, testnet=True)
else:
    client = Client(api_key, api_secret)

RISK_PERCENTAGE = float(os.getenv('RISK_PERCENTAGE', 0.01)) # e.g., 0.01 for 1% risk per trade
ACCOUNT_SIZE = float(os.getenv('ACCOUNT_SIZE', 1000)) # Account size in USDT

def position_size(potential_loss, risk_percentage, account_size):
    if potential_loss <= 0:
        raise ValueError("Potential loss must be greater than zero.")
    
    trade_size = (risk_percentage * account_size) / potential_loss
    return trade_size

def adjust_stop_loss(trade, current_price, stop_loss, trailing_stop=False):
    if not trailing_stop:
        return stop_loss

    new_stop_loss = max(stop_loss, current_price - (current_price * stop_loss))
    return new_stop_loss

@safe_api_call
def manage_trade(trade, broker):
    if trade.isopen:
        current_price = trade.data.close[-1]
        trade.params.stop_loss = adjust_stop_loss(trade, current_price, trade.params.stop_loss, trailing_stop=True)

        if current_price <= trade.params.stop_loss:
            logging.info(f"Selling {trade.size} {trade.data._name} @ {current_price} for a loss")
            try:
                order = client.order_market_sell(
                    symbol=symbol,
                    quantity=trade.size
                )
                logging.info(f"Placed {order['executedQty']} {symbol} sell order at market price")
                trade.close()
                insert_trade(broker, order, 'sell', 'market')
            except BinanceAPIException as e:
                logging.error(e)
        elif current_price >= trade.params.take_profit:
            logging.info(f"Selling {trade.size} {trade.data._name} @ {current_price} for a profit")
            try:
                order = client.order_market_sell(
                    symbol=symbol,
                    quantity=trade.size
                )
                logging.info(f"Placed {order['executedQty']} {symbol} sell order at market price")
                trade.close()
                insert_trade(broker, order, 'sell', 'market')
            except BinanceAPIException as e:
                logging.error(e)

@safe_api_call
def get_margin_percentage(symbol):
    """Returns the margin percentage on isolated trades for the given symbol."""
    account = client.futures_account()
    for balance in account['userAssets']:
        if balance['asset'] == symbol:
            return float(balance['isolatedMarginPercent'])
    raise ValueError(f"Symbol {symbol} not found in margin data.")
