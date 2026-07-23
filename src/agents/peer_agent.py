"""
Peer Comparison Agent
Identifies comparable companies and collects key metrics for relative analysis.
"""

import logging
from typing import Dict, Any, List, Optional
import sys
from pathlib import Path

import yfinance as yf

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# Curated peer sets for common large-cap tickers. yfinance's industry
# constituent lookup ranks by index weight within a narrow industry bucket
# (e.g. "Consumer Electronics"), which surfaces tiny, largely irrelevant
# names (Sonos, Turtle Beach) ahead of the mega-cap peers an analyst would
# actually compare against. These take priority over that lookup.
CURATED_PEERS = {
    "AAPL": ["MSFT", "GOOGL", "005930.KS", "AVGO"],   # Microsoft, Alphabet, Samsung, Broadcom
    "MSFT": ["AAPL", "GOOGL", "AMZN", "ORCL"],
    "GOOGL": ["MSFT", "META", "AMZN", "AAPL"],
    "AMZN": ["MSFT", "GOOGL", "WMT", "BABA"],
    "NVDA": ["AMD", "INTC", "AVGO", "TSM"],
    "META": ["GOOGL", "SNAP", "PINS", "MSFT"],
    "TSLA": ["GM", "F", "RIVN", "TM"],
    "JPM": ["BAC", "WFC", "C", "GS"],
    "GS": ["MS", "JPM", "C", "BAC"],
    "MS": ["GS", "JPM", "C", "BAC"],
    "BAC": ["JPM", "WFC", "C", "GS"],
    "WFC": ["JPM", "BAC", "C", "USB"],
}

# Fallback peers by sector, used when yfinance industry lookup fails
SECTOR_FALLBACK_PEERS = {
    "Financial Services": ["JPM", "BAC", "WFC", "C", "GS"],
    "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "AVGO"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "Consumer Defensive": ["WMT", "PG", "KO", "PEP", "COST"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "Industrials": ["CAT", "GE", "HON", "UNP", "RTX"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "TMUS"],
    "Utilities": ["NEE", "SO", "DUK", "CEG", "AEP"],
    "Real Estate": ["PLD", "AMT", "EQIX", "SPG", "O"],
    "Basic Materials": ["LIN", "SHW", "APD", "ECL", "FCX"],
}


class PeerComparisonAgent:
    """
    Responsible for comparable companies (comps) analysis.

    Responsibilities:
    - Identify 3-4 peer companies in the same industry/sector
    - Fetch key comparison metrics for target and peers
    - Provide raw numeric values so the UI can rank and highlight
    """

    MAX_PEERS = 4
    MIN_PEERS = 3
    MIN_PEER_MARKET_CAP = 1_000_000_000  # exclude sub-$1B names from lookup-based peers

    def __init__(self):
        """Initialize the Peer Comparison Agent"""
        self.name = "Peer Comparison Agent"
        logger.info(f"{self.name} initialized")

    def run(self, ticker: str) -> Dict[str, Any]:
        """
        Build peer comparison for a given ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'JPM')

        Returns:
            Dictionary with target and peer metrics. "companies" holds the
            target first, then peers, each with raw numeric metric values
            (percent units for growth/margin/roe) or None when unavailable.
        """
        logger.info(f"Building peer comparison for {ticker}")

        try:
            target_info = yf.Ticker(ticker).info

            if not target_info or not (target_info.get("shortName") or target_info.get("longName")):
                return {
                    "ticker": ticker,
                    "success": False,
                    "error": f"Could not fetch company info for {ticker}"
                }

            sector = target_info.get("sector", "")
            industry = target_info.get("industry", "")

            candidates = self._find_peer_candidates(ticker, target_info)

            if not candidates:
                return {
                    "ticker": ticker,
                    "success": False,
                    "error": f"Could not identify peer companies for {ticker}"
                }

            target_row = self._extract_metrics(ticker, target_info)
            peers = self._collect_peer_metrics(candidates, target_row)

            if not peers:
                return {
                    "ticker": ticker,
                    "success": False,
                    "error": "No peer metrics could be fetched"
                }

            if len(peers) < self.MIN_PEERS:
                logger.warning(f"Only {len(peers)} peers found for {ticker} (wanted {self.MIN_PEERS}-{self.MAX_PEERS})")

            return {
                "ticker": ticker,
                "success": True,
                "sector": sector,
                "industry": industry,
                "target": target_row,
                "peers": peers,
                "companies": [target_row] + peers,
            }

        except Exception as e:
            logger.error(f"Error building peer comparison: {str(e)}")
            return {
                "ticker": ticker,
                "success": False,
                "error": str(e)
            }

    def _find_peer_candidates(self, ticker: str, target_info: Dict[str, Any]) -> List[str]:
        """Find candidate peer tickers, largest industry players first"""

        # Preferred: curated large-cap peer set, hand-picked for relevance
        curated = CURATED_PEERS.get(ticker.upper())
        if curated:
            return curated

        # Next: yfinance industry constituents (dynamic, market-weight ordered)
        industry_key = target_info.get("industryKey")
        if industry_key:
            try:
                top = yf.Industry(industry_key).top_companies
                if top is not None and not top.empty:
                    return [sym for sym in top.index.tolist() if sym.upper() != ticker.upper()]
            except Exception as e:
                logger.warning(f"Industry peer lookup failed for {ticker}: {str(e)}")

        # Fallback: curated large caps for the sector
        sector = target_info.get("sector", "")
        fallback = SECTOR_FALLBACK_PEERS.get(sector, [])
        return [sym for sym in fallback if sym.upper() != ticker.upper()]

    def _collect_peer_metrics(self, candidates: List[str], target_row: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch metrics for candidates until MAX_PEERS collected, skipping dual listings"""

        peers = []
        seen_names = {self._normalize_name(target_row.get("company"))}

        for symbol in candidates:
            if len(peers) >= self.MAX_PEERS:
                break

            try:
                info = yf.Ticker(symbol).info
            except Exception as e:
                logger.warning(f"Could not fetch peer info for {symbol}: {str(e)}")
                continue

            # Filter out tiny/irrelevant names surfaced by the industry lookup.
            # Skip only when market cap is known and below the floor - missing
            # data (common for some foreign primaries) shouldn't disqualify a peer.
            market_cap = info.get("marketCap")
            if market_cap is not None and market_cap < self.MIN_PEER_MARKET_CAP:
                logger.info(f"Excluding {symbol} from peers: market cap below $1B floor")
                continue

            row = self._extract_metrics(symbol, info)
            if not row.get("company"):
                continue

            # Same company can appear under multiple listings (e.g. BK and BNY)
            name_key = self._normalize_name(row["company"])
            if name_key in seen_names:
                continue

            seen_names.add(name_key)
            peers.append(row)

        return peers

    @staticmethod
    def _normalize_name(name: Optional[str]) -> str:
        """Normalize a company name for duplicate detection across listings"""
        if not name:
            return ""
        cleaned = name.lower()
        for noise in [",", ".", "corporation", "incorporated", "company", "corp", "inc", "the ", "& co", "plc"]:
            cleaned = cleaned.replace(noise, "")
        return " ".join(cleaned.split())

    @staticmethod
    def _extract_metrics(symbol: str, info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract raw comparison metrics from a yfinance info dict"""

        def as_percent(value):
            return round(value * 100, 2) if isinstance(value, (int, float)) else None

        def as_number(value):
            return round(value, 2) if isinstance(value, (int, float)) else None

        return {
            "ticker": symbol.upper(),
            "company": info.get("shortName") or info.get("longName"),
            "pe_ratio": as_number(info.get("trailingPE")),
            "revenue_growth": as_percent(info.get("revenueGrowth")),
            "profit_margin": as_percent(info.get("profitMargins")),
            "roe": as_percent(info.get("returnOnEquity")),
            # yfinance debtToEquity is already scaled (e.g. 96.5 = 0.97x equity)
            "debt_to_equity": as_number(info.get("debtToEquity")),
        }
