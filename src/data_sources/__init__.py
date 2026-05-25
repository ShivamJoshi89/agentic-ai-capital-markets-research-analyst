"""
Data sources module for fetching financial data
"""

from .yfinance_client import YFinanceClient
from .sec_edgar_client import SECEdgarClient
from .news_client import NewsClient
from .fred_client import FREDClient

__all__ = [
    "YFinanceClient",
    "SECEdgarClient",
    "NewsClient",
    "FREDClient",
]