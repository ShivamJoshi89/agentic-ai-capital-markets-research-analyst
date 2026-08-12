"""
Market Data Agent
Collects and analyzes stock price data, returns, volatility, moving averages, etc.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_sources.yfinance_client import YFinanceClient
from analytics.technical_indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class MarketDataAgent:
    """
    Responsible for collecting and analyzing stock market data.
    
    Responsibilities:
    - Fetch historical stock prices
    - Calculate returns (1M, 3M, 6M, YTD)
    - Calculate volatility
    - Calculate moving averages (20, 50, 200 day)
    - Calculate maximum drawdown
    - Analyze price trends
    """
    
    def __init__(self):
        """Initialize the Market Data Agent"""
        self.name = "Market Data Agent"
        self.yfinance_client = YFinanceClient()
        logger.info(f"{self.name} initialized")
    
    def run(self, ticker: str) -> Dict[str, Any]:
        """
        Analyze market data for a given ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'JPM')
        
        Returns:
            Dictionary with market metrics
        """
        logger.info(f"Analyzing market data for {ticker}")
        
        try:
            # Fetch stock data
            stock_data = self.yfinance_client.get_stock_data(ticker, period="1y")
            
            if not stock_data or not stock_data["success"]:
                logger.error(f"Failed to fetch stock data for {ticker}")
                return {
                    "ticker": ticker,
                    "success": False,
                    "error": "Failed to fetch stock data"
                }
            
            history = stock_data["history"]
            
            # Calculate metrics
            metrics = self._calculate_metrics(history)
            
            return {
                "ticker": ticker,
                "success": True,
                "data": history,
                "metrics": metrics
            }
        
        except Exception as e:
            logger.error(f"Error in market data analysis: {str(e)}")
            return {
                "ticker": ticker,
                "success": False,
                "error": str(e)
            }
    
    def _calculate_metrics(self, history: pd.DataFrame) -> Dict[str, Any]:
        """Calculate financial metrics from price history"""
        
        try:
            # Get latest price
            latest_price = history["Close"].iloc[-1]
            previous_price = history["Close"].iloc[-2]

            # Windowed trailing returns. Each window needs strictly more than
            # `window` rows of history behind the latest bar; a shorter series
            # (e.g. a recent IPO) returns None rather than silently borrowing
            # history.iloc[0] under every window's label - previously all of
            # 1M/3M/6M collapsed to the same full-history figure whenever the
            # window exceeded the available history. None matches the MA/
            # max_drawdown N/A convention already used below.
            def windowed_return(window_days: int) -> Optional[float]:
                if len(history) <= window_days:
                    return None
                base_price = history["Close"].iloc[len(history) - window_days]
                return (latest_price / base_price - 1) * 100

            one_month_return = windowed_return(21)    # ~21 trading days
            three_month_return = windowed_return(63)  # ~63 trading days
            six_month_return = windowed_return(126)   # ~126 trading days

            # Calendar year-to-date: base off the first trading bar of the
            # latest bar's calendar year, NOT history.iloc[0]. Against the
            # rolling period="1y" fetch this method is called with,
            # history.iloc[0] is ~12 months back, so the old
            # latest/iloc[0] - 1 was a trailing-twelve-month return
            # mislabeled as "YTD" (confirmed: on a series spanning a year
            # boundary the two differed by tens of percentage points).
            # Anchored to the latest bar's calendar year (not wall-clock
            # today) so a stale or backtest series still yields a coherent
            # YTD. In early January, before a second current-year bar
            # exists, it falls back to the full trailing series and labels
            # that explicitly via ytd_basis so a consumer never presents a
            # since-inception figure as calendar-YTD.
            latest_year = history.index[-1].year
            ytd_rows = history[history.index.year == latest_year]
            if len(ytd_rows) >= 2:
                ytd_base_price = ytd_rows["Close"].iloc[0]
                ytd_basis = "calendar_ytd"
            else:
                ytd_base_price = history["Close"].iloc[0]
                ytd_basis = "trailing_since_series_start"
            ytd_return = (latest_price / ytd_base_price - 1) * 100

            # Calculate daily returns
            daily_returns = history["Close"].pct_change()
            
            # Calculate volatility (annualized)
            volatility = TechnicalIndicators.calculate_volatility(daily_returns, annualized=True)
            
            # Calculate moving averages
            ma_20 = TechnicalIndicators.calculate_moving_average(history["Close"], 20)
            ma_50 = TechnicalIndicators.calculate_moving_average(history["Close"], 50)
            ma_200 = TechnicalIndicators.calculate_moving_average(history["Close"], 200)
            
            # Calculate maximum drawdown
            max_drawdown = TechnicalIndicators.calculate_max_drawdown(history["Close"])
            
            # Average volume
            avg_volume = history["Volume"].mean()
            
            metrics = {
                "latest_price": round(latest_price, 2),
                "previous_price": round(previous_price, 2),
                "price_change": round(latest_price - previous_price, 2),
                "price_change_pct": round((latest_price / previous_price - 1) * 100, 2),
                "one_month_return": round(one_month_return, 2) if one_month_return is not None else None,
                "three_month_return": round(three_month_return, 2) if three_month_return is not None else None,
                "six_month_return": round(six_month_return, 2) if six_month_return is not None else None,
                "ytd_return": round(ytd_return, 2),
                # "calendar_ytd" (base = first bar of the current calendar
                # year) or "trailing_since_series_start" (early-January
                # fallback - no current-year bar yet, so this is a trailing
                # figure and must not be presented as YTD).
                "ytd_basis": ytd_basis,
                "volatility": round(volatility * 100, 2) if volatility else None,
                "ma_20": round(ma_20.iloc[-1], 2) if not pd.isna(ma_20.iloc[-1]) else None,
                "ma_50": round(ma_50.iloc[-1], 2) if not pd.isna(ma_50.iloc[-1]) else None,
                "ma_200": round(ma_200.iloc[-1], 2) if not pd.isna(ma_200.iloc[-1]) else None,
                "max_drawdown": round(max_drawdown * 100, 2) if max_drawdown else None,
                "avg_volume": int(avg_volume),
                "latest_volume": int(history["Volume"].iloc[-1])
            }
            
            return metrics
        
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            return {}