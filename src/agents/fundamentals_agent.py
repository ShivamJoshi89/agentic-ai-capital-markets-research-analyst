"""
Financial Fundamentals Agent
Collects and analyzes company financial statements and ratios.
"""

import logging
from typing import Dict, Any
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_sources.yfinance_client import YFinanceClient

logger = logging.getLogger(__name__)


class FinancialsAgent:
    """
    Responsible for collecting and analyzing company financial data.
    
    Responsibilities:
    - Fetch company fundamentals (revenue, net income, etc.)
    - Calculate financial ratios (P/E, P/B, debt-to-equity, etc.)
    - Analyze profitability and financial health
    - Compare to peers and historical trends
    """
    
    def __init__(self):
        """Initialize the Fundamentals Agent"""
        self.name = "Financial Fundamentals Agent"
        self.yfinance_client = YFinanceClient()
        logger.info(f"{self.name} initialized")
    
    def run(self, ticker: str) -> Dict[str, Any]:
        """
        Analyze financial fundamentals for a given ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'JPM')
        
        Returns:
            Dictionary with financial metrics and ratios
        """
        logger.info(f"Analyzing fundamentals for {ticker}")
        
        try:
            # Fetch fundamentals
            fundamentals = self.yfinance_client.get_fundamentals(ticker)
            
            if not fundamentals or not fundamentals.get("success"):
                logger.error(f"Failed to fetch fundamentals for {ticker}")
                return {
                    "ticker": ticker,
                    "success": False,
                    "error": "Failed to fetch fundamentals"
                }
            
            # Clean and format data
            formatted_data = self._format_fundamentals(fundamentals)
            
            return {
                "ticker": ticker,
                "success": True,
                "fundamentals": formatted_data
            }
        
        except Exception as e:
            logger.error(f"Error analyzing fundamentals: {str(e)}")
            return {
                "ticker": ticker,
                "success": False,
                "error": str(e)
            }
    
    def _format_fundamentals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format fundamentals for display"""

        formatted = {
            # Income Statement
            "revenue": self._format_number(data.get("revenue")),
            "net_income": self._format_number(data.get("net_income")),
            "free_cash_flow": self._format_number(data.get("free_cash_flow")),
            "operating_cash_flow": self._format_number(data.get("operating_cash_flow")),
            
            # Balance Sheet
            "total_assets": self._format_number(data.get("total_assets")),
            "total_liabilities": self._format_number(data.get("total_liabilities")),
            "total_equity": self._format_number(data.get("total_equity")),
            "total_debt": self._format_number(data.get("total_debt")),
            "cash": self._format_number(data.get("cash")),
            
            # Profitability
            "gross_margin": self._format_percentage(data.get("gross_margin")),
            "operating_margin": self._format_percentage(data.get("operating_margin")),
            "profit_margin": self._format_percentage(data.get("profit_margin")),
            "roe": self._format_percentage(data.get("roe")),
            "roa": self._format_percentage(data.get("roa")),
            
            # Valuation
            "eps": self._format_number(data.get("eps"), decimals=2),
            "pe_ratio": self._format_number(data.get("pe_ratio"), decimals=2),
            "pb_ratio": self._format_number(data.get("pb_ratio"), decimals=2),
            "dividend_yield": self._format_dividend_yield(data.get("dividend_yield")),

            # Leverage
            "debt_to_equity": self._format_number(data.get("debt_to_equity"), decimals=2),
            "current_ratio": self._format_number(data.get("current_ratio"), decimals=2),
            "quick_ratio": self._format_number(data.get("quick_ratio"), decimals=2),
        }

        # yfinance leaves several standard metrics empty for financial-sector
        # companies (banks measure leverage via regulatory capital, and FCF is
        # distorted by lending flows) - explain instead of showing bare N/A
        if data.get("sector") == "Financial Services":
            if data.get("debt_to_equity") is None:
                formatted["debt_to_equity"] = (
                    "N/A - D/E ratio uses different leverage metrics for financial institutions"
                )
            if data.get("free_cash_flow") is None:
                formatted["free_cash_flow"] = (
                    "N/A - FCF is not a standard metric for financial institutions"
                )

        return formatted
    
    @staticmethod
    def _format_number(value, decimals=0):
        """Format number for display"""
        if value is None:
            return "N/A"
        try:
            if isinstance(value, (int, float)):
                if decimals == 0:
                    return f"{value:,.0f}"
                else:
                    return f"{value:,.{decimals}f}"
        except:
            return "N/A"
        return "N/A"
    
    @staticmethod
    def _format_percentage(value):
        """Format percentage for display"""
        if value is None:
            return "N/A"
        try:
            if isinstance(value, (int, float)):
                return f"{value*100:.2f}%"
        except:
            return "N/A"
        return "N/A"

    @staticmethod
    def _format_dividend_yield(value):
        """Format dividend yield for display.

        Unlike margins/ROE (returned as fractions), yfinance >= 0.2.54 returns
        dividendYield already expressed in percent (e.g. 1.74 for 1.74%),
        so no x100 scaling is applied here.
        """
        if value is None:
            return "N/A"
        try:
            if isinstance(value, (int, float)):
                return f"{value:.2f}%"
        except:
            return "N/A"
        return "N/A"