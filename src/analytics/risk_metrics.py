"""
Risk metrics calculations
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RiskMetrics:
    """
    Calculates risk metrics for portfolio and company analysis.
    """
    
    @staticmethod
    def calculate_var(returns, confidence_level: float = 0.95) -> Optional[float]:
        """
        Calculate Value at Risk (VaR)
        """
        return returns.quantile(1 - confidence_level)