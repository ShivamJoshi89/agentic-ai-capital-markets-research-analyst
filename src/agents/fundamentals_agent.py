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
            # "year_ago_average" (standard basis), "point_in_time_fallback"
            # (no valid year-ago period found), or "unavailable_fallback".
            "equity_average_basis": data.get("equity_average_basis"),
            "assets_average_basis": data.get("assets_average_basis"),
            "equity_average_row": data.get("equity_average_row"),
            # "computed" (gross/operating margin recomputed as a TTM ratio from
            # the income statement) or "info_fallback" (yfinance's precomputed
            # value, used when the statement couldn't support a recompute).
            "gross_margin_basis": data.get("gross_margin_basis"),
            "operating_margin_basis": data.get("operating_margin_basis"),
            # Raw float (percent) or None - consumed by the financing-risk
            # layer to distinguish balance-sheet growth from contraction for
            # the cash-runway sector exemption. Passed through unformatted.
            "total_assets_yoy_change_pct": data.get("total_assets_yoy_change_pct"),

            # Valuation
            "eps": self._format_number(data.get("eps"), decimals=2),
            "pe_ratio": self._format_number(data.get("pe_ratio"), decimals=2),
            "pb_ratio": self._format_number(data.get("pb_ratio"), decimals=2),
            # "computed" (market cap / equity, both same currency) or
            # "info_fallback_unverified" (no FX rate available to convert a
            # foreign issuer's equity, so this is yfinance's own precomputed
            # priceToBook - independently observed wrong for at least one
            # real ADR, so it's surfaced as unverified rather than trusted).
            "pb_ratio_basis": data.get("pb_ratio_basis"),
            "dividend_yield": self._format_dividend_yield(data.get("dividend_yield")),

            # Leverage
            "debt_to_equity": self._format_debt_to_equity(data.get("debt_to_equity")),
            "current_ratio": self._format_number(data.get("current_ratio"), decimals=2),
            "quick_ratio": self._format_number(data.get("quick_ratio"), decimals=2),

            "sector": data.get("sector"),
            # Sector classification, resolved once here so every downstream
            # consumer (this card's gating below, the Risk Agent's P/E check,
            # the UI's sector info boxes) reads a single source of truth
            # rather than re-deriving sector string comparisons independently.
            # yfinance groups banks AND insurers under "Financial Services"
            # and REITs under "Real Estate".
            "is_financial_sector": data.get("sector") == "Financial Services",
            "is_reit": data.get("sector") == "Real Estate",

            # Period disclosure: income-statement figures above (revenue,
            # net_income, eps, margins) are TTM as of financials_period_end;
            # balance-sheet figures (total_assets, total_equity, etc.) are a
            # point-in-time snapshot as of balance_sheet_period_end, which can
            # legitimately lag the income-statement cutoff by a quarter or
            # more since 10-Q/10-K filings post later than the earnings print.
            "financials_period_end": data.get("financials_period_end"),
            "balance_sheet_period_end": data.get("balance_sheet_period_end"),

            # Currency disclosure: revenue/net_income/total_assets/
            # total_liabilities/total_equity/total_debt/cash/free_cash_flow/
            # operating_cash_flow above are converted to USD using this
            # conversion (foreign private issuers report in a home
            # currency) when fx_conversion["applied"] is True. When it's
            # False but native_currency is set, FX data wasn't available
            # and those same fields are still in native_currency - callers
            # must not render them with a "$" prefix in that case.
            "fx_conversion": data.get("fx_conversion") or {"applied": False, "native_currency": None},
        }

        # Metrics that are structurally absent/meaningless for financial
        # institutions (banks & insurers): no current/non-current balance-
        # sheet split (so neither a current nor a quick ratio), and no
        # reported cost of goods (so no gross margin). Gated UNCONDITIONALLY
        # for the sector - not only when yfinance's own value happens to be
        # missing - because yfinance sometimes populates a plausible-looking
        # grossMargins/currentRatio/quickRatio for a financial company that
        # the page's own disclaimer explicitly states isn't a bank metric;
        # letting that leak through contradicted the disclaimer and showed a
        # real-looking figure that means nothing here.
        if formatted["is_financial_sector"]:
            formatted["gross_margin"] = "N/A"
            formatted["current_ratio"] = "N/A"
            formatted["quick_ratio"] = "N/A"

        # Negative shareholders' equity: D/E, P/B, and ROE all divide by
        # equity, and a negative denominator produces a signed number that
        # reads backwards (e.g. a profitable company shows a *negative*
        # "ROE", implying a loss that didn't happen). Render as N/A rather
        # than a misleading multiple - matching the same principle already
        # applied to negative P/E in peer comparison.
        total_equity = data.get("total_equity")
        formatted["negative_equity"] = isinstance(total_equity, (int, float)) and total_equity < 0
        if formatted["negative_equity"]:
            formatted["debt_to_equity"] = "N/A (negative equity)"
            formatted["pb_ratio"] = "N/A (negative equity)"
            formatted["roe"] = "N/A (negative equity)"

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
    def _format_debt_to_equity(value):
        """Format debt-to-equity as a multiple.

        yfinance's debtToEquity (and our statement-computed fallback) is
        percent-scaled: 154.0 means debt is 1.54x equity.
        """
        if value is None:
            return "N/A"
        try:
            if isinstance(value, (int, float)):
                return f"{value / 100:.2f}x"
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