import logging
from unittest.mock import Mock

from curl_cffi.requests.exceptions import Timeout
import pandas as pd
import pytest

from src import providers


VALID_INFO = {
    "symbol": "AAPL",
    "regularMarketPrice": 200.0,
    "regularMarketVolume": 1000,
}


def test_returns_quote_for_valid_symbol(monkeypatch):
    monkeypatch.setattr(
        providers.yf,
        "Ticker",
        lambda symbol: Mock(info=VALID_INFO),
    )

    result = providers.YFinanceProvider().get_quote("AAPL")

    assert result == {
        "symbol": "AAPL",
        "price": 200.0,
        "volume": 1000,
    }


def test_returns_none_when_quote_data_is_missing(monkeypatch, caplog):
    monkeypatch.setattr(
        providers.yf,
        "Ticker",
        lambda symbol: Mock(info={}),
    )

    result = providers.YFinanceProvider().get_quote("NOTREAL")

    assert result is None
    assert "No usable quote data returned for NOTREAL" in caplog.text


def test_retries_timeout_then_succeeds(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    ticker = Mock(
        side_effect=[
            Timeout("temporary timeout"),
            Mock(info=VALID_INFO),
        ]
    )
    sleep = Mock()
    monkeypatch.setattr(providers.yf, "Ticker", ticker)
    monkeypatch.setattr(providers.time, "sleep", sleep)

    result = providers.YFinanceProvider().get_quote("AAPL")

    assert result["symbol"] == "AAPL"
    assert ticker.call_count == 2
    assert [call.args[0] for call in sleep.call_args_list] == [1]
    assert "attempt 1/4" in caplog.text
    assert "after 1 timeout retries" in caplog.text


def test_returns_none_after_all_timeout_retries(monkeypatch, caplog):
    ticker = Mock(side_effect=Timeout("timeout"))
    sleep = Mock()
    monkeypatch.setattr(providers.yf, "Ticker", ticker)
    monkeypatch.setattr(providers.time, "sleep", sleep)

    result = providers.YFinanceProvider().get_quote("AAPL")

    assert result is None
    assert ticker.call_count == providers.MAX_TIMEOUT_RETRIES + 1
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2, 4]
    assert "Giving up on quote for AAPL after 3 timeout retries (4 attempts)" in caplog.text


def test_logs_and_returns_none_for_unexpected_exception(monkeypatch, caplog):
    monkeypatch.setattr(
        providers.yf,
        "Ticker",
        Mock(side_effect=RuntimeError("request failed")),
    )

    result = providers.YFinanceProvider().get_quote("AAPL")

    assert result is None
    assert "Failed to fetch or process quote for AAPL" in caplog.text
    assert "request failed" in caplog.text


def test_historical_request_uses_shared_timeout_retries(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    historical_data = pd.DataFrame(
        {"Close": [200.0], "Volume": [1000]},
        index=pd.to_datetime(["2025-01-02"]),
    )
    historical_data.index.name = "Date"

    first_history_call = Mock(side_effect=Timeout("temporary timeout"))
    first_ticker = Mock()
    first_ticker.history = first_history_call

    second_history_call = Mock(return_value=historical_data)
    second_ticker = Mock()
    second_ticker.history = second_history_call

    ticker = Mock(side_effect=[first_ticker, second_ticker])
    sleep = Mock()
    monkeypatch.setattr(providers.yf, "Ticker", ticker)
    monkeypatch.setattr(providers.time, "sleep", sleep)

    result = providers.YFinanceProvider().get_historical_data("AAPL")

    assert result == {
        "symbol": "AAPL",
        "price": [200.0],
        "volume": [1000],
        "date": [pd.Timestamp("2025-01-02")],
    }
    assert ticker.call_count == 2
    sleep.assert_called_once_with(1)
    assert "Fetched historical data for AAPL after 1 timeout retries" in caplog.text
