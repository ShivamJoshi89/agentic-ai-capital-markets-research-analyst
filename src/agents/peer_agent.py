"""
Peer Comparison Agent
Identifies comparable companies and collects key metrics for relative analysis.

Peer discovery is fully dynamic: every bracket and filter scales off the
target company's own market cap and revenue, and candidates are sourced live
from yfinance on every call. There is no hardcoded peer list and no fixed
dollar threshold, so the same logic works for a micro-cap and a mega-cap
alike.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yfinance as yf

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# Sector -> SPDR sector ETF. This is a fixed taxonomy mapping (11 sectors to
# their standard sector ETF), not a peer list - the ETF's actual holdings are
# fetched fresh from yfinance every run and change as the market does.
SECTOR_ETF_MAP = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Energy": "XLE",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}


class PeerComparisonAgent:
    """
    Responsible for comparable companies (comps) analysis.

    Three-layer dynamic filter, all scaled off the target company itself:

    Layer 1 - Market cap bracket: candidates must fall within [0.1x, 10x]
              of the target's market cap (relaxed to [0.01x, 100x] if that
              band yields fewer than 2 peers).
    Layer 2 - Industry match score: +3 for an exact industryKey match,
              +1 for a same-sector match. Used to rank candidates; a
              same-industry small-cap will outrank a same-sector mega-cap.
    Layer 3 - Revenue scale filter: candidates must fall within
              [0.05x, 20x] of the target's revenue, screening out shell
              companies, SPACs, and holding companies that only
              coincidentally share a market cap or industry classification.

    Candidates are sourced from two live pools, unioned together:
      - the target sector's SPDR ETF top holdings (breadth - surfaces the
        mega-cap names that dominate the sector), and
      - yfinance's industryKey constituents (precision - the ETF pool is
        cap-weighted and top-10-only, so it cannot represent a narrow
        industry or a company that isn't a top-10-by-weight sector name;
        the industry pool is what actually finds peers for a mid-cap like
        a footwear or regional-bank name).
    Both are pure lookups against live yfinance data - neither is a fixed
    list of tickers.
    """

    MAX_PEERS = 4
    MIN_PEERS_REQUIRED = 2  # below this, relax the market cap bracket and retry

    MARKET_CAP_BRACKET: Tuple[float, float] = (0.1, 10)
    MARKET_CAP_BRACKET_RELAXED: Tuple[float, float] = (0.01, 100)
    REVENUE_BRACKET: Tuple[float, float] = (0.05, 20)

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

            target_market_cap = target_info.get("marketCap")
            target_revenue = target_info.get("totalRevenue")
            sector = target_info.get("sector", "")
            industry = target_info.get("industry", "")
            industry_key = target_info.get("industryKey")

            if not target_market_cap:
                return {
                    "ticker": ticker,
                    "success": False,
                    "error": f"No market cap data for {ticker} - cannot size a peer bracket"
                }

            candidate_symbols = self._source_candidates(ticker, sector, industry_key)
            if not candidate_symbols:
                return {
                    "ticker": ticker,
                    "success": False,
                    "error": f"Could not identify peer candidates for {ticker}"
                }

            candidate_infos = self._fetch_candidate_infos(candidate_symbols)

            peers = self._select_peers(
                target_info, candidate_infos, sector, industry_key,
                target_market_cap, target_revenue, self.MARKET_CAP_BRACKET
            )

            if len(peers) < self.MIN_PEERS_REQUIRED:
                logger.info(
                    f"Only {len(peers)} peer(s) for {ticker} within "
                    f"{self.MARKET_CAP_BRACKET}x cap bracket; relaxing to {self.MARKET_CAP_BRACKET_RELAXED}x"
                )
                peers = self._select_peers(
                    target_info, candidate_infos, sector, industry_key,
                    target_market_cap, target_revenue, self.MARKET_CAP_BRACKET_RELAXED
                )

            if not peers:
                return {
                    "ticker": ticker,
                    "success": False,
                    "error": "No peer metrics could be fetched"
                }

            target_row = self._extract_metrics(ticker, target_info)

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

    def _source_candidates(self, ticker: str, sector: str, industry_key: Optional[str]) -> List[str]:
        """Union of two live candidate pools; neither is a fixed peer list.

        Sourcing both (rather than treating industryKey as an error-only
        fallback) matters in practice: a sector ETF's top-10 holdings are
        cap-weighted and dominated by mega-caps, so for anything that isn't
        itself a top-10-by-weight name (e.g. a $10-20B mid-cap), the ETF
        pool alone would never surface a same-industry peer.
        """

        symbols: List[str] = []

        etf_symbol = SECTOR_ETF_MAP.get(sector)
        if etf_symbol:
            try:
                holdings = yf.Ticker(etf_symbol).funds_data.top_holdings
                if holdings is not None and not holdings.empty:
                    symbols.extend(holdings.index.tolist())
            except Exception as e:
                logger.warning(f"Sector ETF lookup ({etf_symbol}) failed for {ticker}: {str(e)}")

        if industry_key:
            try:
                top = yf.Industry(industry_key).top_companies
                if top is not None and not top.empty:
                    symbols.extend(top.index.tolist())
            except Exception as e:
                logger.warning(f"Industry lookup ({industry_key}) failed for {ticker}: {str(e)}")

        # De-dupe (first-seen order), drop the target itself
        seen = set()
        candidates = []
        for sym in symbols:
            sym_upper = sym.upper()
            if sym_upper == ticker.upper() or sym_upper in seen:
                continue
            seen.add(sym_upper)
            candidates.append(sym_upper)

        return candidates

    @staticmethod
    def _fetch_candidate_infos(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch yfinance info for each candidate once, so both the normal
        and relaxed selection passes can reuse it without re-fetching."""

        infos = {}
        for symbol in symbols:
            try:
                info = yf.Ticker(symbol).info
            except Exception as e:
                logger.warning(f"Could not fetch candidate info for {symbol}: {str(e)}")
                continue
            if info and (info.get("shortName") or info.get("longName")):
                infos[symbol] = info
        return infos

    def _select_peers(
        self,
        target_info: Dict[str, Any],
        candidate_infos: Dict[str, Dict[str, Any]],
        sector: str,
        industry_key: Optional[str],
        target_market_cap: float,
        target_revenue: Optional[float],
        cap_bracket: Tuple[float, float],
    ) -> List[Dict[str, Any]]:
        """Apply the market-cap bracket (Layer 1) and revenue-scale filter
        (Layer 3), score by industry match (Layer 2), and return the top
        MAX_PEERS ranked by score then by closeness in market cap."""

        cap_min = target_market_cap * cap_bracket[0]
        cap_max = target_market_cap * cap_bracket[1]
        revenue_min = target_revenue * self.REVENUE_BRACKET[0] if target_revenue else None
        revenue_max = target_revenue * self.REVENUE_BRACKET[1] if target_revenue else None

        target_name_key = self._normalize_name(target_info.get("shortName") or target_info.get("longName"))

        scored = []
        for symbol, info in candidate_infos.items():
            market_cap = info.get("marketCap")
            if market_cap is None or not (cap_min <= market_cap <= cap_max):
                continue

            revenue = info.get("totalRevenue")
            if revenue_min is not None and revenue is not None and not (revenue_min <= revenue <= revenue_max):
                continue

            score = 0
            if industry_key and info.get("industryKey") == industry_key:
                score = 3
            elif sector and info.get("sector") == sector:
                score = 1

            if score == 0:
                continue

            scored.append((score, market_cap, symbol, info))

        # Rank by industry match first, then by proximity in market cap
        scored.sort(key=lambda item: (-item[0], abs(item[1] - target_market_cap)))

        peers = []
        seen_names = {target_name_key}

        for score, market_cap, symbol, info in scored:
            if len(peers) >= self.MAX_PEERS:
                break

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
