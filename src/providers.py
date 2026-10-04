import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Optional, Sequence, TypeVar, TypedDict

from pandas import Timestamp

from curl_cffi.requests.exceptions import Timeout
import yfinance as yf


MAX_TIMEOUT_RETRIES = 3
MAX_CONCURRENT_QUOTES = 3
_Result = TypeVar("_Result")


class Quote(TypedDict):
    symbol: str
    price: float
    volume: int


class StockHistory(TypedDict):
    symbol: str
    price: list[float]
    volume: list[int]
    date: list[Timestamp]


logger = logging.getLogger(__name__)


class YFinanceProvider:

    ''' Provider class for YahooFinance. '''

    def get_quotes(self, symbols: Sequence[str]) -> List[Optional[Quote]]:
        if not symbols:
            return []

        with ThreadPoolExecutor(
            max_workers=min(MAX_CONCURRENT_QUOTES, len(symbols))
        ) as executor:
            return list(executor.map(self.get_quote, symbols))

    def _request_with_retries(
        self,
        symbol: str,
        data_kind: str,
        request: Callable[[], Optional[_Result]],
    ) -> Optional[_Result]:
        for retry_count in range(MAX_TIMEOUT_RETRIES + 1):
            try:
                result = request()
                if retry_count and result is not None:
                    logger.info(
                        "Fetched %s for %s after %d timeout retries",
                        data_kind,
                        symbol,
                        retry_count,
                    )
                return result
            except Timeout as exc:
                logger.warning(
                    "Timeout fetching %s for %s on attempt %d/%d: %s",
                    data_kind,
                    symbol,
                    retry_count + 1,
                    MAX_TIMEOUT_RETRIES + 1,
                    exc,
                )
                if retry_count < MAX_TIMEOUT_RETRIES:
                    time.sleep(2**retry_count)
                else:
                    logger.error(
                        "Giving up on %s for %s after %d timeout retries "
                        "(%d attempts)",
                        data_kind,
                        symbol,
                        MAX_TIMEOUT_RETRIES,
                        MAX_TIMEOUT_RETRIES + 1,
                    )
            except Exception:
                logger.exception("Failed to fetch or process %s for %s", data_kind, symbol)
                return None

        return None

    def get_quote(self, symbol: str) -> Optional[Quote]:
        '''
        Requests stock quote for a given symbol from yahoo finance.

        :param symbol: The request stock symbol
        :type symbol: str
        :return: Quote data including symbol, price, and volume
        :rtype: Quote | None
        '''
        def fetch_quote() -> Optional[Quote]:
            stock_info = yf.Ticker(symbol).info
            required_fields = (
                "symbol",
                "regularMarketPrice",
                "regularMarketVolume",
            )
            if not stock_info or any(
                field not in stock_info or stock_info[field] is None
                for field in required_fields
            ):
                logger.warning("No usable quote data returned for %s", symbol)
                return None

            return Quote(
                symbol=stock_info["symbol"],
                price=stock_info["regularMarketPrice"],
                volume=stock_info["regularMarketVolume"],
            )

        return self._request_with_retries(symbol, "quote", fetch_quote)

    def get_historical_data(
        self,
        symbol: str,
        *,
        period: Optional[str] = None,
        interval: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Optional[StockHistory]:

        range_arguments = (interval, start, end)
        has_range_argument = any(value is not None for value in range_arguments)

        if period is not None and has_range_argument:
            raise ValueError(
                "period cannot be combined with interval, start, or end"
            )
        if has_range_argument and not all(
            value is not None for value in range_arguments
        ):
            raise ValueError("interval, start, and end must be provided together")
        if period is None and not has_range_argument:
            period = "1y"

        def fetch_history() -> Optional[StockHistory]:
            stock = yf.Ticker(symbol)
            if has_range_argument:
                historical_data = stock.history(start=start, end=end, interval=interval)
            else:
                historical_data = stock.history(period=period)

            historical_data = historical_data.reset_index()
            if historical_data.empty:
                logger.warning("No usable historical data returned for %s", symbol)
                return None

            historical_data = historical_data.rename(columns={"Close": "price", "Volume": "volume", "Date": "date"})
            historical_data = historical_data[["date", "price", "volume"]]
            final_records = historical_data.to_dict()
            final_records = {k: list(inner.values()) for k, inner in final_records.items()}

            return StockHistory(
                symbol=symbol,
                price=final_records['price'],
                volume=final_records['volume'],
                date=final_records['date']
            )

        return self._request_with_retries(symbol, "historical data", fetch_history)
