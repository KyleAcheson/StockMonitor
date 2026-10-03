import logging
import time
from typing import Optional, TypedDict
from curl_cffi.requests.exceptions import Timeout
import yfinance as yf


MAX_TIMEOUT_RETRIES = 3


class Quote(TypedDict):
    symbol: str
    price: float
    volume: int


logger = logging.getLogger(__name__)


class YFinanceProvider:

    ''' Provider class for YahooFinance. '''

    def get_quote(self, symbol: str) -> Optional[Quote]:
        '''
        Requests stock quote for a given symbol from yahoo finance.

        :param symbol: The request stock symbol
        :type symbol: str
        :return: Quote data including symbol, price, and volume
        :rtype: Quote | None
        '''
        for retry_count in range(MAX_TIMEOUT_RETRIES + 1):
            try:
                stock = yf.Ticker(symbol)
                stock_info = stock.info
                required_fields = (
                    "symbol",
                    "regularMarketPrice",
                    "regularMarketVolume",
                )
                if not stock_info or any(
                    field not in stock_info or stock_info[field] is None
                    for field in required_fields
                ):
                    logger.warning("No usable stock data returned for %s", symbol)
                    return None

                if retry_count:
                    logger.info(
                        "Fetched stock data for %s after %d timeout retries",
                        symbol,
                        retry_count,
                    )
                return Quote(
                    symbol=stock_info["symbol"],
                    price=stock_info["regularMarketPrice"],
                    volume=stock_info["regularMarketVolume"],
                )
            except Timeout as exc:
                logger.warning(
                    "Timeout fetching stock data for %s on attempt %d/%d: %s",
                    symbol,
                    retry_count + 1,
                    MAX_TIMEOUT_RETRIES + 1,
                    exc,
                )
                if retry_count < MAX_TIMEOUT_RETRIES:
                    time.sleep(2**retry_count)
                else:
                    logger.error(
                        "Giving up on %s after %d timeout retries (%d attempts)",
                        symbol,
                        MAX_TIMEOUT_RETRIES,
                        MAX_TIMEOUT_RETRIES + 1,
                    )
            except Exception:
                logger.exception("Failed to fetch stock data for %s", symbol)
                return None

        return None