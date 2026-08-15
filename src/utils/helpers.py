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

    # A 1-5 letter base, optionally followed by a "-XX" class/preferred/
    # warrant/unit suffix (1-2 letters): e.g. AAPL, BRK-B, BEP-PA, BKSY-WT,
    # VII-UN. The earlier "^[A-Z]{1,5}$" rejected every hyphenated security -
    # a regression against the 100-ticker sweep, which confirmed the pipeline
    # handled exactly these (BEP-PA/BKSY-WT/GSL-PB/LZM-WT/MAA-PI/OPP-PA/
    # TRTN-PG/VII-UN) gracefully. Still rejects the cases this guard exists for
    # (digits, spaces, quotes/semicolons, empty) since only [A-Z] and a single
    # optional hyphen are permitted, capped at 8 chars.
    pattern = r"^[A-Z]{1,5}(-[A-Z]{1,2})?$"
    return bool(re.match(pattern, ticker.strip()))