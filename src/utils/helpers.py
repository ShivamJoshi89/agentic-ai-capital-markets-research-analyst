"""
Helper functions
"""

import re
import logging

logger = logging.getLogger(__name__)


def validate_ticker(ticker: str) -> bool:
    """
    Validate stock ticker format.
    
    Args:
        ticker: Ticker symbol (e.g., 'JPM')
    
    Returns:
        True if valid, False otherwise
    """
    if not ticker or not isinstance(ticker, str):
        return False
    
    # Tickers are 1-5 uppercase letters
    pattern = r"^[A-Z]{1,5}$"
    return bool(re.match(pattern, ticker.strip()))