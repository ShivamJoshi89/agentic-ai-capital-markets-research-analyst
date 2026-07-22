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

            # The info dict lacks several fields (all balance-sheet totals, and
            # for banks also leverage/liquidity ratios) - fall back to the
            # financial statement DataFrames for those
            balance_sheet = self._safe_statement(stock, "balance_sheet")
            cashflow = self._safe_statement(stock, "cashflow")

            total_assets = info.get("totalAssets") or self._latest_row(
                balance_sheet, ["Total Assets"])
            total_liabilities = info.get("totalLiabilities") or self._latest_row(
                balance_sheet, ["Total Liabilities Net Minority Interest", "Total Liab"])
            total_equity = info.get("totalEquity") or self._latest_row(
                balance_sheet, ["Stockholders Equity", "Common Stock Equity",
                                "Total Equity Gross Minority Interest"])
            total_debt = info.get("totalDebt") or self._latest_row(
                balance_sheet, ["Total Debt"])
            operating_cash_flow = info.get("operatingCashflow") or self._latest_row(
                cashflow, ["Operating Cash Flow"])
            free_cash_flow = info.get("freeCashflow") or self._latest_row(
                cashflow, ["Free Cash Flow"])

            # debtToEquity is percent-scaled in yfinance (154.0 = 1.54x);
            # keep the computed fallback on the same scale
            debt_to_equity = info.get("debtToEquity")
            if debt_to_equity is None and total_debt and total_equity:
                debt_to_equity = round(total_debt / total_equity * 100, 2)

            # Liquidity ratios from the current asset/liability split when the
            # info dict lacks them (banks report neither - stays None there)
            current_ratio = info.get("currentRatio")
            quick_ratio = info.get("quickRatio")
            if current_ratio is None or quick_ratio is None:
                current_assets = self._latest_row(balance_sheet, ["Current Assets"])
                current_liabilities = self._latest_row(balance_sheet, ["Current Liabilities"])
                if current_assets and current_liabilities:
                    if current_ratio is None:
                        current_ratio = round(current_assets / current_liabilities, 2)
                    if quick_ratio is None:
                        inventory = self._latest_row(balance_sheet, ["Inventory"]) or 0
                        quick_ratio = round((current_assets - inventory) / current_liabilities, 2)

            fundamentals = {
                "ticker": ticker,
                "sector": info.get("sector", None),
                "revenue": info.get("totalRevenue", None),
                "net_income": info.get("netIncomeToCommon", None),
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "total_equity": total_equity,
                "total_debt": total_debt,
                "cash": info.get("totalCash", None),
                "free_cash_flow": free_cash_flow,
                "operating_cash_flow": operating_cash_flow,
                "gross_margin": info.get("grossMargins", None),
                "operating_margin": info.get("operatingMargins", None),
                "profit_margin": info.get("profitMargins", None),
                "roe": info.get("returnOnEquity", None),
                "roa": info.get("returnOnAssets", None),
                "eps": info.get("trailingEps", None),
                "pe_ratio": info.get("trailingPE", None),
                "pb_ratio": info.get("priceToBook", None),
                "dividend_yield": info.get("dividendYield", None),
                "debt_to_equity": debt_to_equity,
                "current_ratio": current_ratio,
                "quick_ratio": quick_ratio,
                "success": True
            }

            return fundamentals

        except Exception as e:
            logger.error(f"Error fetching fundamentals for {ticker}: {str(e)}")
            return None

    @staticmethod
    def _safe_statement(stock, attribute: str):
        """Fetch a financial statement DataFrame, returning None on any failure"""
        try:
            statement = getattr(stock, attribute)
            if statement is None or statement.empty:
                return None
            return statement
        except Exception as e:
            logger.warning(f"Could not fetch {attribute}: {str(e)}")
            return None

    @staticmethod
    def _latest_row(statement, row_names) -> Optional[float]:
        """Most recent non-null value for the first matching row name.
        Statement columns are ordered most-recent first."""
        if statement is None:
            return None
        for name in row_names:
            if name in statement.index:
                series = statement.loc[name].dropna()
                if not series.empty:
                    return float(series.iloc[0])
        return None