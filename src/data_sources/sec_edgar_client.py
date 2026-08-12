"""
SEC EDGAR API client for fetching official filing data
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import Config

logger = logging.getLogger(__name__)

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_nodash}/{primary_doc}"

# Registration/shelf forms and prospectus supplements (shelf takedowns - how
# ATM programs and equity lines actually get drawn on).
#
# EFFECT (notice of effectiveness) is deliberately NOT here: it's a routine
# notice that a registration statement has been declared effective and applies
# to ANY registration - including S-8 employee stock plans, which aren't a
# capital-raising event - and the recent-filings feed doesn't say which
# registration a given EFFECT belongs to, so it can't be distinguished from an
# S-8 effectiveness. When an EFFECT does correspond to a real S-1/S-3, that
# underlying form is already counted directly below, so counting EFFECT too
# would double-count the same financing event and inflate the filing count
# that drives the overhang severity. The substantive events (S-1/S-3/424B)
# are captured on their own.
FINANCING_FORMS = {
    "S-1": "Registration statement (S-1)",
    "S-1/A": "Registration statement amendment (S-1/A)",
    "S-3": "Shelf registration (S-3)",
    "S-3/A": "Shelf registration amendment (S-3/A)",
    "S-3ASR": "Automatic shelf registration (S-3ASR)",
    "424B3": "Prospectus supplement (424B3)",
    "424B4": "Prospectus supplement (424B4)",
    "424B5": "Prospectus supplement / shelf takedown (424B5)",
}

# 8-K items that commonly disclose financing-related events
FINANCING_8K_ITEMS = {
    "1.01": "Item 1.01 - entry into a material definitive agreement",
    "3.02": "Item 3.02 - unregistered sales of equity securities",
    "3.03": "Item 3.03 - material modification to security holder rights",
}


def classify_financing_filing(form: str, items: str = "") -> Optional[str]:
    """
    Pure function, no I/O. Returns a short reason string if the filing looks
    financing-related, else None. form is the SEC form type; items is the
    comma-separated 8-K item list (only populated when form == "8-K").
    """
    if form in FINANCING_FORMS:
        return FINANCING_FORMS[form]

    if form == "8-K" and items:
        item_list = [i.strip() for i in items.split(",") if i.strip()]
        matched = [i for i in item_list if i in FINANCING_8K_ITEMS]
        if matched:
            reasons = ", ".join(FINANCING_8K_ITEMS[i] for i in matched)
            return reasons

    return None


class SECEdgarClient:
    """
    Client for fetching data from SEC EDGAR.
    """

    _ticker_cik_map: Optional[Dict[str, str]] = None

    def __init__(self):
        """Initialize SEC EDGAR client"""
        self.name = "SEC EDGAR Client"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": Config.SEC_USER_AGENT})
        logger.info(f"{self.name} initialized")

    def ticker_to_cik(self, ticker: str) -> Optional[str]:
        """
        Convert ticker symbol to a 10-digit zero-padded CIK.

        Args:
            ticker: Stock ticker symbol

        Returns:
            10-digit zero-padded CIK string, or None if not found/on error
        """
        try:
            if SECEdgarClient._ticker_cik_map is None:
                logger.info("Loading SEC ticker->CIK map")
                response = self.session.get(TICKERS_URL, timeout=15)
                response.raise_for_status()
                data = response.json()

                ticker_map = {}
                for entry in data.values():
                    entry_ticker = str(entry.get("ticker", "")).upper()
                    cik = entry.get("cik_str")
                    if entry_ticker and cik is not None:
                        ticker_map[entry_ticker] = str(cik).zfill(10)

                SECEdgarClient._ticker_cik_map = ticker_map

            return SECEdgarClient._ticker_cik_map.get(ticker.upper())

        except Exception as e:
            logger.warning(f"Could not resolve CIK for ticker {ticker}: {str(e)}")
            return None

    def get_submissions(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Fetch filer metadata and recent filings from SEC EDGAR.

        Args:
            cik: 10-digit zero-padded Central Index Key

        Returns:
            Dictionary with submissions data or None if error
        """
        try:
            url = SUBMISSIONS_URL.format(cik=cik)
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Could not fetch submissions for CIK {cik}: {str(e)}")
            return None

    def get_company_facts(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Fetch XBRL company facts from SEC EDGAR.

        Args:
            cik: 10-digit zero-padded Central Index Key

        Returns:
            Dictionary with company facts or None if error
        """
        try:
            url = COMPANY_FACTS_URL.format(cik=cik)
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Could not fetch company facts for CIK {cik}: {str(e)}")
            return None

    def get_recent_filings(self, cik: str, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Fetch recent filings for a CIK, newest first.

        Args:
            cik: 10-digit zero-padded Central Index Key
            limit: Maximum number of filings to return

        Returns:
            List of {form, filing_date, accession_number, items, url} dicts
        """
        submissions = self.get_submissions(cik)
        if not submissions:
            return []

        try:
            cik_int = int(cik)
            recent = submissions.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            filing_dates = recent.get("filingDate", [])
            accession_numbers = recent.get("accessionNumber", [])
            items = recent.get("items", [])
            primary_documents = recent.get("primaryDocument", [])

            filings = []
            for i in range(min(len(forms), limit)):
                accession_number = accession_numbers[i] if i < len(accession_numbers) else ""
                primary_document = primary_documents[i] if i < len(primary_documents) else ""
                accession_nodash = accession_number.replace("-", "")

                url = ""
                if accession_nodash and primary_document:
                    url = ARCHIVES_URL.format(
                        cik_int=cik_int,
                        accession_nodash=accession_nodash,
                        primary_doc=primary_document,
                    )

                filings.append({
                    "form": forms[i],
                    "filing_date": filing_dates[i] if i < len(filing_dates) else "",
                    "accession_number": accession_number,
                    "items": items[i] if i < len(items) else "",
                    "url": url,
                })

            return filings

        except Exception as e:
            logger.warning(f"Could not parse recent filings for CIK {cik}: {str(e)}")
            return []

    def get_financing_filings(self, cik: str, since_days: int = 548,
                               limit: int = 200) -> List[Dict[str, Any]]:
        """
        Fetch recent filings that look financing-related (shelf registrations,
        prospectus supplements, and 8-Ks disclosing dilutive financing events).

        Args:
            cik: 10-digit zero-padded Central Index Key
            since_days: Lookback window in days (default ~18 months)
            limit: Maximum number of recent filings to scan

        Returns:
            List of filings with a "reason" field attached, newest first
        """
        filings = self.get_recent_filings(cik, limit=limit)
        if not filings:
            return []

        try:
            cutoff = datetime.now() - timedelta(days=since_days)
            financing_filings = []

            for filing in filings:
                try:
                    filing_date = datetime.strptime(filing["filing_date"], "%Y-%m-%d")
                except (ValueError, KeyError):
                    continue

                if filing_date < cutoff:
                    continue

                reason = classify_financing_filing(filing["form"], filing.get("items", ""))
                if reason:
                    filing_with_reason = dict(filing)
                    filing_with_reason["reason"] = reason
                    financing_filings.append(filing_with_reason)

            return financing_filings

        except Exception as e:
            logger.warning(f"Could not filter financing filings for CIK {cik}: {str(e)}")
            return []

    def get_shares_outstanding_series(self, cik: str) -> List[Dict[str, Any]]:
        """
        Fetch shares-outstanding history from XBRL company facts.

        Args:
            cik: 10-digit zero-padded Central Index Key

        Returns:
            List of {"end": "YYYY-MM-DD", "shares": float} sorted oldest to
            newest, de-duplicated by period end (latest filed date wins)
        """
        facts = self.get_company_facts(cik)
        if not facts:
            return []

        try:
            fact_tree = facts.get("facts", {})

            shares_data = fact_tree.get("dei", {}).get(
                "EntityCommonStockSharesOutstanding", {}
            ).get("units", {}).get("shares")

            if not shares_data:
                shares_data = fact_tree.get("us-gaap", {}).get(
                    "CommonStockSharesOutstanding", {}
                ).get("units", {}).get("shares")

            if not shares_data:
                logger.warning(f"No shares outstanding data found for CIK {cik}")
                return []

            # De-duplicate by period end, preferring the row with the latest
            # "filed" date (restatements supersede original filings)
            by_end = {}
            for row in shares_data:
                end = row.get("end")
                val = row.get("val")
                filed = row.get("filed", "")
                if end is None or val is None:
                    continue

                existing = by_end.get(end)
                if existing is None or filed > existing["filed"]:
                    by_end[end] = {"end": end, "shares": float(val), "filed": filed}

            series = sorted(by_end.values(), key=lambda r: r["end"])
            return [{"end": r["end"], "shares": r["shares"]} for r in series]

        except Exception as e:
            logger.warning(f"Could not parse shares outstanding for CIK {cik}: {str(e)}")
            return []
