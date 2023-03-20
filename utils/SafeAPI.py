# import pdb; pdb.set_trace() # Debug Mode
import logging
import time
import os
from binance.exceptions import BinanceAPIException, BinanceRequestException

# Configure logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/SafeAPI.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Define maximum number of retries and delay time between retries
MAX_RETRIES = 5
RETRY_DELAY = 0.5  # in seconds

def safe_api_call(api_call_func):
    """
    Decorator function for safely making API calls with retries and rate limiting.
    """
    def wrapper(*args, **kwargs):
        retry_count = 0
        while retry_count < MAX_RETRIES:
            try:
                # Make the API call
                response = api_call_func(*args, **kwargs)
                # Return the response if successful
                return response
            except BinanceAPIException as e:
                # If the error is related to rate limiting, wait and retry
                if e.status_code == 429:
                    retry_count += 1
                    time.sleep(RETRY_DELAY)
                else:
                    # If the error is not related to rate limiting, log the error and raise an exception
                    logging.error(f"API call failed with error code {e.status_code}: {e.message}", exc_info=True)
                    raise e
            except BinanceRequestException as e:
                # If the error is related to a network error, wait and retry
                if "ConnectionError" in str(e):
                    retry_count += 1
                    time.sleep(RETRY_DELAY)
                else:
                    # If the error is not related to a network error, log the error and raise an exception
                    logging.error(f"API call failed with error message: {e.message}", exc_info=True)
                    raise e
            except Exception as e:
                # If the error is not related to Binance API or network errors, log the error and raise an exception
                logging.error(f"API call failed with error: {e}", exc_info=True)
                raise e

        # If maximum number of retries reached, log the error and raise an exception
        error_msg = f"API call failed after {MAX_RETRIES} retries"
        logging.error(error_msg)
        raise Exception(error_msg)

    return wrapper
