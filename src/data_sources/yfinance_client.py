"""
yfinance client for fetching stock market data
"""

import logging
from typing import Dict, Any, Optional
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


class YFinanceClient:
    """
    Client for fetching stock data from yfinance.
    """
    
    def __init__(self):
        """Initialize YFinance client"""
        self.name = "YFinance Client"
        logger.info(f"{self.name} initialized")
    
    def get_stock_data(self, ticker: str, period: str = "1y") -> Optional[Dict[str, Any]]:
        """
        Fetch historical stock data.
        
        Args:
            ticker: Stock ticker symbol
            period: Time period ('1y', '5y', etc.)
        
        Returns:
            Dictionary with stock data or None if error
        """
        try:
            logger.info(f"Fetching stock data for {ticker} ({period})")
            
            # Create ticker object
            stock = yf.Ticker(ticker)
            
            # Fetch historical data
            history = stock.history(period=period)
            
            if history.empty:
                logger.warning(f"No data found for {ticker}")
                return None
            
            return {
                "ticker": ticker,
                "history": history,
                "period": period,
                "success": True
            }
        
        except Exception as e:
            logger.error(f"Error fetching stock data for {ticker}: {str(e)}")
            return None
    
    def get_company_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch company information.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with company info or None if error
        """
        try:
            logger.info(f"Fetching company info for {ticker}")
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info:
                logger.warning(f"No info found for {ticker}")
                return None
            
            # Extract key information
            company_data = {
                "ticker": ticker,
                "company_name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", None),
                "employees": info.get("fullTimeEmployees", None),
                "website": info.get("website", ""),
                "country": info.get("country", ""),
                "currency": info.get("currency", "USD"),
                "exchange": info.get("exchange", ""),
                "business_summary": info.get("longBusinessSummary", ""),
                "current_price": info.get("currentPrice", None),
                "previous_close": info.get("previousClose", None),
                "open_price": info.get("open", None),
                "day_high": info.get("dayHigh", None),
                "day_low": info.get("dayLow", None),
                "52_week_high": info.get("fiftyTwoWeekHigh", None),
                "52_week_low": info.get("fiftyTwoWeekLow", None),
                "success": True
            }
            
            return company_data
        
        except Exception as e:
            logger.error(f"Error fetching company info for {ticker}: {str(e)}")
            return None
    
    def get_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch company fundamentals.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with financial data or None if error
        """
        try:
            logger.info(f"Fetching fundamentals for {ticker}")
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info:
                logger.warning(f"No fundamentals found for {ticker}")
                return None
            
            fundamentals = {
                "ticker": ticker,
                "sector": info.get("sector", None),
                "revenue": info.get("totalRevenue", None),
                "net_income": info.get("netIncomeToCommon", None),
                "total_assets": info.get("totalAssets", None),
                "total_liabilities": info.get("totalLiabilities", None),
                "total_equity": info.get("totalEquity", None),
                "total_debt": info.get("totalDebt", None),
                "cash": info.get("totalCash", None),
                "free_cash_flow": info.get("freeCashflow", None),
                "operating_cash_flow": info.get("operatingCashflow", None),
                "gross_margin": info.get("grossMargins", None),
                "operating_margin": info.get("operatingMargins", None),
                "profit_margin": info.get("profitMargins", None),
                "roe": info.get("returnOnEquity", None),
                "roa": info.get("returnOnAssets", None),
                "eps": info.get("trailingEps", None),
                "pe_ratio": info.get("trailingPE", None),
                "pb_ratio": info.get("priceToBook", None),
                "dividend_yield": info.get("dividendYield", None),
                "debt_to_equity": info.get("debtToEquity", None),
                "current_ratio": info.get("currentRatio", None),
                "quick_ratio": info.get("quickRatio", None),
                "success": True
            }
            
            return fundamentals
        
        except Exception as e:
            logger.error(f"Error fetching fundamentals for {ticker}: {str(e)}")
            return None