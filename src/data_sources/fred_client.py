"""
FRED API client for fetching macroeconomic data
Uses the fredapi library with a FRED API key (Config.FRED_API_KEY).
Falls back gracefully to None values if the key or library is unavailable.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

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

# FX series for foreign-issuer currency conversion (financial statements in
# a foreign private issuer's home currency, e.g. an ADR reporting in JPY
# while trading in USD). Value: (FRED series ID, invert). FRED quotes some
# pairs as "foreign units per 1 USD" (invert=True - divide to get USD, or
# equivalently take the reciprocal) and others as "USD per 1 foreign unit"
# (invert=False - use directly). Only currencies verified live against a
# real FRED pull are listed; an unmapped currency means conversion isn't
# attempted rather than risking a wrong, unverified series ID.
FX_SERIES_MAP: Dict[str, Tuple[str, bool]] = {
    "JPY": ("DEXJPUS", True),   # Japanese Yen per USD
    "DKK": ("DEXDNUS", True),   # Danish Krone per USD
    "CHF": ("DEXSZUS", True),   # Swiss Franc per USD
    "CAD": ("DEXCAUS", True),   # Canadian Dollar per USD
    "EUR": ("DEXUSEU", False),  # USD per Euro
    "GBP": ("DEXUSUK", False),  # USD per British Pound
    # Added after a 100-ticker validation sweep found ADRs reporting in these
    # currencies (e.g. HDB/INR, ITUB/BBD/PBR/BRL, BABA/CNY) were left
    # unconverted - correctly labeled native, but not USD - because their
    # currency wasn't mapped. All verified live against a real FRED pull
    # (rates produced sane USD magnitudes, e.g. HDB revenue 2.95T INR ->
    # $31B, matching HDFC Bank's real ~$30-40B). All DEX*US series quote
    # foreign-per-USD (invert=True); DEXUSAL quotes USD-per-AUD (invert=False).
    "INR": ("DEXINUS", True),   # Indian Rupee per USD
    "BRL": ("DEXBZUS", True),   # Brazilian Real per USD
    "KRW": ("DEXKOUS", True),   # South Korean Won per USD
    "TWD": ("DEXTAUS", True),   # Taiwan Dollar per USD
    "HKD": ("DEXHKUS", True),   # Hong Kong Dollar per USD
    "MXN": ("DEXMXUS", True),   # Mexican Peso per USD
    "CNY": ("DEXCHUS", True),   # Chinese Yuan per USD
    "SGD": ("DEXSIUS", True),   # Singapore Dollar per USD
    "SEK": ("DEXSDUS", True),   # Swedish Krona per USD
    "NOK": ("DEXNOUS", True),   # Norwegian Krone per USD
    "AUD": ("DEXUSAL", False),  # USD per Australian Dollar
}


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
                    "fed_rate_value": self._get_latest_value(SERIES_FED_FUNDS),
                    "10y_treasury": self._get_treasury_yield(),
                    "10y_treasury_value": self._get_latest_value(SERIES_10Y_TREASURY),
                    "unemployment_rate": self._get_unemployment(),
                    "unemployment_rate_value": self._get_latest_value(SERIES_UNEMPLOYMENT),
                    "cpi_inflation": self._get_cpi_inflation(),
                    "cpi_inflation_value": self._compute_cpi_yoy_inflation(),
                    "vix_index": self._get_vix(),
                    "vix_index_value": self._get_latest_value(SERIES_VIX),
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

    def _compute_cpi_yoy_inflation(self) -> Optional[float]:
        """Compute CPI YoY inflation as a raw float (percent units, e.g. 3.2 = 3.2%)"""
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
            return (latest / year_ago - 1) * 100
        except Exception as e:
            logger.warning(f"Could not compute CPI inflation: {str(e)}")
            return None

    def _get_cpi_inflation(self) -> Optional[str]:
        """Get CPI Inflation YoY (CPIAUCSL index, year-over-year change)"""
        value = self._compute_cpi_yoy_inflation()
        if value is None:
            return None
        return f"{value:.1f}% YoY"

    def _get_vix(self) -> Optional[str]:
        """Get VIX Volatility Index (VIXCLS)"""
        value = self._get_latest_value(SERIES_VIX)
        if value is None:
            return None
        return f"{value:.2f}"

    def get_fx_rate_to_usd(self, currency: str) -> Optional[Dict[str, Any]]:
        """
        Latest USD-per-1-unit conversion factor for `currency` - multiplying
        a `currency`-denominated amount by the returned rate gives its USD
        equivalent.

        Args:
            currency: ISO currency code (e.g. "JPY")

        Returns:
            {"rate": float, "as_of": "YYYY-MM-DD"}, or None if `currency`
            is already "USD" (no conversion needed - use 1.0 directly),
            isn't in FX_SERIES_MAP, FRED is unavailable, or the series
            returned no data.
        """
        if not currency or currency == "USD":
            return None

        mapping = FX_SERIES_MAP.get(currency)
        if not mapping or self.fred is None:
            return None

        series_id, invert = mapping
        try:
            series = self.fred.get_series(series_id).dropna()
            if series.empty:
                logger.warning(f"FX series {series_id} returned no data")
                return None
            raw_rate = float(series.iloc[-1])
            rate = (1 / raw_rate) if invert else raw_rate
            as_of = series.index[-1]
            return {
                "rate": rate,
                "as_of": as_of.date().isoformat() if hasattr(as_of, "date") else str(as_of),
            }
        except Exception as e:
            logger.warning(f"Could not fetch FX rate for {currency} ({series_id}): {str(e)}")
            return None
