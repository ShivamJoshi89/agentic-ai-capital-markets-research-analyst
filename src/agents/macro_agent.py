"""
Macro Agent
Retrieves and analyzes macroeconomic indicators.
"""

import logging
from typing import Dict, Any
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_sources.fred_client import FREDClient

logger = logging.getLogger(__name__)


class MacroAgent:
    """
    Responsible for retrieving and analyzing macroeconomic data.
    
    Responsibilities:
    - Retrieve federal funds rate
    - Retrieve Treasury yields
    - Retrieve inflation (CPI) data
    - Retrieve unemployment rate
    - Assess macro impact on sector and company
    """
    
    def __init__(self):
        """Initialize the Macro Agent"""
        self.name = "Macro Agent"
        self.fred_client = FREDClient()
        logger.info(f"{self.name} initialized")
    
    def run(self, ticker: str = None, sector: str = None) -> Dict[str, Any]:
        """
        Retrieve and analyze macroeconomic indicators.
        
        Args:
            ticker: Stock ticker symbol (optional)
            sector: Company sector (optional)
        
        Returns:
            Dictionary with macro data and analysis
        """
        logger.info(f"Retrieving macroeconomic indicators")
        
        try:
            # Fetch macro data
            macro_data = self.fred_client.get_macro_indicators()
            
            if not macro_data.get("success"):
                logger.warning("Failed to fetch macro data")
                return {
                    "success": False,
                    "error": "Failed to fetch macro indicators"
                }
            
            # Generate macro analysis
            analysis = self._analyze_macro_impact(macro_data.get("data", {}), sector)
            
            return {
                "success": True,
                "indicators": macro_data.get("data", {}),
                "analysis": analysis,
                "sector": sector
            }
        
        except Exception as e:
            logger.error(f"Error in macro analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _analyze_macro_impact(self, indicators: Dict[str, Any], sector: str = None) -> Dict[str, str]:
        """Analyze macro impact on markets and sectors"""
        
        analysis = {
            "interest_rates": self._analyze_rates(indicators.get("fed_rate")),
            "treasury_impact": self._analyze_treasury(indicators.get("10y_treasury")),
            "inflation_impact": self._analyze_inflation(indicators.get("cpi_inflation")),
            "labor_market": self._analyze_labor(indicators.get("unemployment_rate")),
            "volatility": indicators.get("vix_index", "N/A"),
            "summary": self._generate_summary(sector)
        }
        
        return analysis
    
    @staticmethod
    def _analyze_rates(fed_rate):
        """Analyze Fed rate impact"""
        if not fed_rate:
            return "Fed rate data unavailable"
        
        return (
            f"Federal Funds Rate: {fed_rate}. Higher rates can support fixed income "
            "but may pressure growth stocks and borrowing costs."
        )
    
    @staticmethod
    def _analyze_treasury(treasury):
        """Analyze Treasury yield impact"""
        if not treasury:
            return "Treasury yield data unavailable"
        
        return (
            f"10-Year Treasury Yield: {treasury}. Affects long-term borrowing costs "
            "and valuation multiples across sectors."
        )
    
    @staticmethod
    def _analyze_inflation(inflation):
        """Analyze inflation impact"""
        if not inflation:
            return "Inflation data unavailable"
        
        return (
            f"CPI Inflation: {inflation}. Inflation impacts consumer purchasing power "
            "and company margins, affecting discretionary and defensive sectors differently."
        )
    
    @staticmethod
    def _analyze_labor(unemployment):
        """Analyze labor market impact"""
        if not unemployment:
            return "Unemployment data unavailable"
        
        return (
            f"Unemployment Rate: {unemployment}. Labor market strength affects "
            "consumer spending and wage inflation."
        )
    
    @staticmethod
    def _generate_summary(sector: str = None):
        """Generate macro summary"""
        sector_text = f" for {sector}" if sector else ""
        
        return (
            f"Macroeconomic conditions{sector_text}: Monitor interest rate trajectory, "
            "inflation trends, and employment data for impacts on valuations and earnings. "
            "Consider sector-specific sensitivities to macro factors."
        )