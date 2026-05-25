"""
Technical indicators calculations
"""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """
    Calculates technical indicators for stock analysis.
    """
    
    @staticmethod
    def calculate_moving_average(prices: pd.Series, window: int) -> pd.Series:
        """Calculate moving average"""
        return prices.rolling(window=window).mean()
    
    @staticmethod
    def calculate_volatility(returns: pd.Series, annualized: bool = True) -> Optional[float]:
        """Calculate volatility (standard deviation)"""
        vol = returns.std()
        if annualized:
            vol *= (252 ** 0.5)  # Annualize by 252 trading days
        return vol
    
    @staticmethod
    def calculate_max_drawdown(prices: pd.Series) -> Optional[float]:
        """Calculate maximum drawdown"""
        cummax = prices.cummax()
        drawdown = (prices - cummax) / cummax
        return drawdown.min()