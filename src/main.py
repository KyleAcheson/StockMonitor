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
    stock_list = [
        stock_data
        for stock_data in (yf_provider.get_stock_data(symbol) for symbol in requests)
        if stock_data is not None
    ]
    for stock in stock_list:
        print(stock['symbol'], stock['price'])
    breakpoint()  # Debugging breakpoint

if __name__ == "__main__":
    configure_logging()
    requests = ['AAPL', 'GOOGL', 'MSFT', 'rwfvwcrw']
    main(requests)
