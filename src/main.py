import logging
from pathlib import Path

import providers as providers


def configure_logging():
    repo_root = Path(__file__).resolve().parent.parent
    log_directory = repo_root / ".local"
    log_directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        filename=log_directory / "stockmonitor.log",
        encoding="utf-8",
    )


def main(requests):

    yf_provider = providers.YFinanceProvider()

    quotes = [
        quote
        for quote in (yf_provider.get_quote(symbol) for symbol in requests)
        if quote is not None
    ]
    for quote in quotes:
        print(quote['symbol'], quote['price'])

    history = [
        hist for hist in (yf_provider.get_historical_data(symbol) for symbol in requests)
        if hist is not None
    ]

    for hist in history:
        print(hist['symbol'], hist['price'])

if __name__ == "__main__":
    configure_logging()
    requests = ['AAPL', 'GOOGL', 'MSFT']
    main(requests)
