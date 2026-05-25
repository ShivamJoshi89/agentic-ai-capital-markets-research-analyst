"""
Financial ratios calculations
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class FinancialRatios:
    """
    Calculates financial ratios for fundamental analysis.
    """
    
    @staticmethod
    def calculate_pe_ratio(stock_price: float, eps: float) -> Optional[float]:
        """Calculate Price-to-Earnings ratio"""
        if eps == 0:
            return None
        return stock_price / eps
    
    @staticmethod
    def calculate_debt_to_equity(total_debt: float, total_equity: float) -> Optional[float]:
        """Calculate Debt-to-Equity ratio"""
        if total_equity == 0:
            return None
        return total_debt / total_equity
    
    @staticmethod
    def calculate_profit_margin(net_income: float, revenue: float) -> Optional[float]:
        """Calculate Profit Margin"""
        if revenue == 0:
            return None
        return net_income / revenue