import logging
from pathlib import Path

if __package__:
    from . import providers
else:
    from StockMonitor import providers


def configure_logging():
    repo_root = Path(__file__).resolve().parents[2]
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
        for quote in yf_provider.get_quotes(requests)
        if quote is not None
    ]
    for quote in quotes:
        print(quote['symbol'], quote['price'])

if __name__ == "__main__":
    configure_logging()
    requests = ['AAPL', 'GOOGL', 'MSFT']
    main(requests)
