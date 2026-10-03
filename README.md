# StockMonitor

Application logs are written to `.local/stockmonitor.log` in the repository
root. The `.local/` directory is ignored by Git. The application configures
logging in `src/main.py`; yfinance messages at INFO and above are included
alongside application logs.
