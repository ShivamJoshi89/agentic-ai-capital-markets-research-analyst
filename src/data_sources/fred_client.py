"""
FRED API client for fetching macroeconomic data
Uses the fredapi library with a FRED API key (Config.FRED_API_KEY).
Falls back gracefully to None values if the key or library is unavailable.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import Config

logger = logging.getLogger(__name__)

try:
    from fredapi import Fred
    FREDAPI_AVAILABLE = True
except ImportError:
    FREDAPI_AVAILABLE = False
    logger.warning("fredapi library not installed - macro data will be unavailable")

# FRED series IDs
SERIES_FED_FUNDS = "FEDFUNDS"      # Effective Federal Funds Rate (%)
SERIES_10Y_TREASURY = "DGS10"      # 10-Year Treasury Constant Maturity Rate (%)
SERIES_UNEMPLOYMENT = "UNRATE"     # Civilian Unemployment Rate (%)
SERIES_CPI = "CPIAUCSL"            # CPI for All Urban Consumers (index level)
SERIES_VIX = "VIXCLS"              # CBOE Volatility Index


class FREDClient:
    """
    Client for fetching macroeconomic data from FRED (Federal Reserve Economic Data).

    Requires FRED_API_KEY in the environment. If the key or the fredapi
    library is missing, all indicators return None instead of raising.
    """

    def __init__(self):
        """Initialize FRED client"""
        self.name = "FRED Client"
        self.fred = None

        if not FREDAPI_AVAILABLE:
            logger.warning(f"{self.name}: fredapi not installed, running without live data")
        elif not Config.FRED_API_KEY:
            logger.warning(f"{self.name}: FRED_API_KEY not set, running without live data")
        else:
            try:
                self.fred = Fred(api_key=Config.FRED_API_KEY)
            except Exception as e:
                logger.error(f"{self.name}: failed to initialize fredapi: {str(e)}")

        logger.info(f"{self.name} initialized (live data: {self.fred is not None})")

    def get_macro_indicators(self) -> Dict[str, Any]:
        """
        Get current macroeconomic indicators from FRED.

        Returns:
            Dictionary with macro data
        """
        try:
            logger.info("Fetching macroeconomic indicators")

            macro_data = {
                "success": True,
                "data": {
                    "fed_rate": self._get_fed_rate(),
                    "10y_treasury": self._get_treasury_yield(),
                    "unemployment_rate": self._get_unemployment(),
                    "cpi_inflation": self._get_cpi_inflation(),
                    "vix_index": self._get_vix(),
                }
            }

            return macro_data

        except Exception as e:
            logger.error(f"Error fetching macro data: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {}
            }

    def _get_latest_value(self, series_id: str) -> Optional[float]:
        """Fetch the most recent non-null observation for a FRED series"""
        if self.fred is None:
            return None

        try:
            series = self.fred.get_series(series_id)
            series = series.dropna()
            if series.empty:
                logger.warning(f"FRED series {series_id} returned no data")
                return None
            return float(series.iloc[-1])
        except Exception as e:
            logger.warning(f"Could not fetch FRED series {series_id}: {str(e)}")
            return None

    def _get_fed_rate(self) -> Optional[str]:
        """Get Effective Federal Funds Rate (FEDFUNDS)"""
        value = self._get_latest_value(SERIES_FED_FUNDS)
        if value is None:
            return None
        return f"{value:.2f}%"

    def _get_treasury_yield(self) -> Optional[str]:
        """Get 10-Year Treasury Yield (DGS10)"""
        value = self._get_latest_value(SERIES_10Y_TREASURY)
        if value is None:
            return None
        return f"{value:.2f}%"

    def _get_unemployment(self) -> Optional[str]:
        """Get Unemployment Rate (UNRATE)"""
        value = self._get_latest_value(SERIES_UNEMPLOYMENT)
        if value is None:
            return None
        return f"{value:.1f}%"

    def _get_cpi_inflation(self) -> Optional[str]:
        """Get CPI Inflation YoY (CPIAUCSL index, year-over-year change)"""
        if self.fred is None:
            return None

        try:
            series = self.fred.get_series(SERIES_CPI).dropna()
            # CPIAUCSL is a monthly index level; YoY inflation needs 13 observations
            if len(series) < 13:
                logger.warning("Not enough CPI data to compute YoY inflation")
                return None
            latest = float(series.iloc[-1])
            year_ago = float(series.iloc[-13])
            yoy_inflation = (latest / year_ago - 1) * 100
            return f"{yoy_inflation:.1f}% YoY"
        except Exception as e:
            logger.warning(f"Could not compute CPI inflation: {str(e)}")
            return None

    def _get_vix(self) -> Optional[str]:
        """Get VIX Volatility Index (VIXCLS)"""
        value = self._get_latest_value(SERIES_VIX)
        if value is None:
            return None
        return f"{value:.2f}"
