"""
Financing & Dilution Risk Agent
Tracks share-count dilution, cash runway, and financing-related SEC filings.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

import yfinance as yf

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_sources.sec_edgar_client import SECEdgarClient

logger = logging.getLogger(__name__)

YOY_MIN_DAYS = 330
QOQ_MIN_DAYS = 75
REVERSE_SPLIT_THRESHOLD_PCT = -40
FORWARD_SPLIT_THRESHOLD_PCT = 90

# Sectors for which negative operating cash flow is a structural feature of
# the balance-sheet-driven business model, NOT a cash-burn / near-insolvency
# signal: a bank's or insurer's operating cash flow is dominated by lending,
# deposit, and reserve flows, and a REIT's by property acquisition, any of
# which can run large and negative in a growth year without implying the
# company is running out of money. Dividing cash by that "burn" produces a
# meaningless runway (confirmed: a bank with loan-growth-driven negative OCF
# tripped a High "Limited Cash Runway"), so the generic burn-rate runway flag
# and its overhang-score contribution are suppressed for these sectors.
# yfinance classifies insurers under "Financial Services" (not a separate
# "Insurance" sector), so these two strings cover banks, insurers, and REITs -
# the three groups where this false signal arises. The runway figure itself is
# still computed and shown; only its interpretation as a *risk* is gated out.
#
# The blanket suppression alone would also wave off a genuinely distressed
# financial (declining deposits / shrinking balance sheet - the 2023 regional-
# bank pattern), which is where the signal matters most. To avoid that, the
# suppression is refined by a cheap, currency-invariant proxy already fetched
# for other purposes: the YoY change in total assets (see
# YFinanceClient._yoy_change_pct). Negative OCF + GROWING assets is funding
# growth (stay suppressed); negative OCF + SHRINKING assets is the opposite
# pattern and gets a distinct, sector-appropriate "Balance Sheet Contraction"
# flag (NOT framed as burn-rate runway).
#
# Documented limitation (deliberately explicit, not silently absorbed): this
# proxy was validated live only on the growth case - the negative-OCF banks
# available in the data (e.g. JPM, C) were all clearly growing, and no live
# financial was simultaneously OCF-negative and asset-shrinking, because banks
# that contract hardest tend to fail and leave the data universe. The
# contraction branch is therefore fixture-validated, and the proxy is coarse:
# it reads total-assets direction only, not deposit-level detail or the reason
# for the change. When the YoY trend is unavailable, it falls back to the
# blanket suppression rather than inventing a signal.
RUNWAY_EXEMPT_SECTORS = {"Financial Services", "Real Estate"}

# A financial's total assets falling below this YoY threshold (percent),
# alongside negative operating cash flow, trips the distinct contraction flag
# instead of the blanket runway suppression. 0.0 = actual shrinkage; flat-to-
# growing stays on the suppressed (growth) side, to avoid flagging a stable
# balance sheet as contracting.
BALANCE_SHEET_CONTRACTION_YOY_PCT = 0.0
# A split's ex-date and the SEC cover-page date nearest it rarely line up
# exactly (different data sources, different snapshot conventions) - allow
# this much slack on each side when matching a magnitude jump to a real
# corporate-action date from yfinance's Ticker.splits.
SPLIT_MATCH_BUFFER_DAYS = 30


class FinancingRiskAgent:
    """
    Responsible for assessing financing and dilution overhang risk.

    Responsibilities:
    - Pull shares-outstanding history from SEC EDGAR, compute YoY and QoQ
      dilution rates
    - Estimate cash runway in months from fundamentals (cash / monthly
      operating burn) - only meaningful when operating cash flow is negative
    - Pull recent financing-related filings via SECEdgarClient
    - Roll all three into flags shaped like Risk Agent's risk dicts
      ({title, category: "Financing", severity, description, metric, impact})
      plus an overall Low/Medium/High overhang_level
    """

    def __init__(self):
        """Initialize the Financing & Dilution Risk Agent"""
        self.name = "Financing & Dilution Risk Agent"
        self.edgar = SECEdgarClient()
        logger.info(f"{self.name} initialized")

    def run(self, ticker: str, fundamentals_data: Optional[Dict[str, Any]] = None,
            company_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Assess financing and dilution risk for a given ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'JPM')
            fundamentals_data: Output of FinancialsAgent.run()
            company_info: Company info dict (used for market cap context)

        Returns:
            Dictionary with dilution, cash runway, financing filings, and flags
        """
        logger.info(f"Analyzing financing/dilution risk for {ticker}")

        try:
            cik = self.edgar.ticker_to_cik(ticker)
            if not cik:
                logger.warning(f"No SEC CIK found for {ticker}")
                return {
                    "ticker": ticker,
                    "success": False,
                    "error": "No SEC EDGAR match for ticker",
                    "cik": None,
                    "dilution": {"available": False},
                    "cash_runway": {"available": False},
                    "financing_filings": [],
                    "flags": [],
                    "overhang_level": "Unknown",
                    "summary": "Financing/dilution data unavailable - no SEC EDGAR match for this ticker."
                }

            dilution = self._analyze_dilution(cik, ticker)
            runway = self._analyze_runway(fundamentals_data)
            financing_filings = self.edgar.get_financing_filings(cik)
            flags = self._build_flags(dilution, runway, financing_filings, company_info)
            overhang_level = self._overhang_level(dilution, runway, financing_filings, company_info)
            summary = self._summarize(overhang_level, dilution, runway, financing_filings)

            return {
                "ticker": ticker,
                "success": True,
                "cik": cik,
                "dilution": dilution,
                "cash_runway": runway,
                "financing_filings": financing_filings,
                "flags": flags,
                "overhang_level": overhang_level,
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"Error analyzing financing/dilution risk for {ticker}: {str(e)}")
            return {
                "ticker": ticker,
                "success": False,
                "error": str(e),
                "cik": None,
                "dilution": {"available": False},
                "cash_runway": {"available": False},
                "financing_filings": [],
                "flags": [],
                "overhang_level": "Unknown",
                "summary": "Financing/dilution analysis failed."
            }

    def _analyze_dilution(self, cik: str, ticker: str) -> Dict[str, Any]:
        """Compute YoY and QoQ share-count dilution from the shares-outstanding series"""

        series = self.edgar.get_shares_outstanding_series(cik)
        if len(series) < 2:
            return {"available": False}

        latest = series[-1]
        yoy_comparator = self._find_comparator(series, latest, min_days=YOY_MIN_DAYS)
        qoq_comparator = self._find_comparator(series, latest, min_days=QOQ_MIN_DAYS)

        dilution = {
            "available": True,
            "latest_shares": latest["shares"],
            "latest_period_end": latest["end"],
            "yoy_change_pct": self._pct_change(yoy_comparator, latest),
            "qoq_change_pct": self._pct_change(qoq_comparator, latest),
            "history": series[-8:],
            "likely_split": False,
        }

        # A jump this steep in either direction is a corporate action, not
        # organic attrition/issuance - take the most recent one, since
        # that's what's shaping the reading. Both directions are checked:
        # a reverse split collapses the share count (large decrease), a
        # forward split expands it (large increase) - a magnitude-only
        # check can't tell either apart from real buybacks/dilution, so
        # real corporate-action data is consulted below before deciding
        # whether to treat it as a split at all.
        split_index = None
        split_direction = None
        for i in range(len(series) - 1):
            change = self._pct_change(series[i], series[i + 1])
            if change is None:
                continue
            if change <= REVERSE_SPLIT_THRESHOLD_PCT:
                split_index = i + 1
                split_direction = "reverse"
            elif change >= FORWARD_SPLIT_THRESHOLD_PCT:
                split_index = i + 1
                split_direction = "forward"

        if split_index is not None:
            split_point = series[split_index]
            prior_point = series[split_index - 1]
            split_events = self._get_split_events(ticker)

            if split_events is not None and self._find_matching_split(
                split_events, prior_point["end"], split_point["end"]
            ):
                confidence = "confirmed"
            elif split_events is not None:
                # Real corporate-action data was available and doesn't
                # corroborate a split near this jump - treat the magnitude
                # jump as genuine (dilution or a large buyback), not a
                # split, and leave the raw reading in place.
                confidence = None
            else:
                # No corporate-action data to consult at all (fetch
                # failed) - fall back to the magnitude-only heuristic,
                # but say so, rather than presenting a guess with the
                # same certainty as a confirmed split.
                confidence = "heuristic"

            if confidence is not None:
                post_split_series = series[split_index:]
                yoy_comparator_ps = self._find_comparator(post_split_series, latest, min_days=YOY_MIN_DAYS)
                qoq_comparator_ps = self._find_comparator(post_split_series, latest, min_days=QOQ_MIN_DAYS)

                dilution.update({
                    "likely_split": True,
                    "split_direction": split_direction,
                    "split_confidence": confidence,
                    "split_detected_at": split_point["end"],
                    "raw_yoy_change_pct": dilution["yoy_change_pct"],
                    "raw_qoq_change_pct": dilution["qoq_change_pct"],
                    "yoy_change_pct": self._pct_change(yoy_comparator_ps, latest),
                    "qoq_change_pct": self._pct_change(qoq_comparator_ps, latest),
                })

        return dilution

    @staticmethod
    def _get_split_events(ticker: str):
        """Fetch yfinance's actual corporate-action split history.

        Returns a pandas Series (index = split date, value = split ratio;
        possibly empty if the ticker has real history but no matching
        event) on success, or None if the fetch itself failed - callers
        treat these two cases differently: an empty-but-successfully-
        fetched series is treated as positive evidence ruling out a split
        near a given date, while None means there's no corporate-action
        data to consult at all.
        """
        try:
            return yf.Ticker(ticker).splits
        except Exception as e:
            logger.warning(f"Could not fetch split history for {ticker}: {str(e)}")
            return None

    @staticmethod
    def _find_matching_split(split_events, window_start: str, window_end: str) -> bool:
        """True if `split_events` (as returned by `_get_split_events`) has
        any entry within SPLIT_MATCH_BUFFER_DAYS of [window_start, window_end]
        (both "YYYY-MM-DD" period-end strings)."""
        if split_events is None or split_events.empty:
            return False

        start = datetime.strptime(window_start, "%Y-%m-%d") - timedelta(days=SPLIT_MATCH_BUFFER_DAYS)
        end = datetime.strptime(window_end, "%Y-%m-%d") + timedelta(days=SPLIT_MATCH_BUFFER_DAYS)

        for split_date in split_events.index:
            naive_date = split_date.to_pydatetime().replace(tzinfo=None)
            if start <= naive_date <= end:
                return True
        return False

    @staticmethod
    def _find_comparator(series: List[Dict[str, Any]], latest: Dict[str, Any],
                          min_days: int) -> Optional[Dict[str, Any]]:
        """
        Find the closest prior data point that is at least min_days before
        the latest point (i.e. the tightest comparator satisfying the
        lookback threshold).
        """
        latest_date = datetime.strptime(latest["end"], "%Y-%m-%d")

        best = None
        best_days = None
        for row in series:
            if row["end"] == latest["end"]:
                continue
            row_date = datetime.strptime(row["end"], "%Y-%m-%d")
            days_back = (latest_date - row_date).days
            if days_back < min_days:
                continue
            if best_days is None or days_back < best_days:
                best = row
                best_days = days_back

        return best

    @staticmethod
    def _pct_change(old: Optional[Dict[str, Any]], new: Optional[Dict[str, Any]]) -> Optional[float]:
        """Percent change in shares outstanding between two series points"""
        if not old or not new:
            return None
        old_shares = old.get("shares")
        new_shares = new.get("shares")
        if not old_shares:
            return None
        return (new_shares - old_shares) / old_shares * 100

    def _analyze_runway(self, fundamentals_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Estimate cash runway in months from cash and operating cash flow"""

        if not fundamentals_data:
            return {"available": False}

        fund = fundamentals_data.get("fundamentals", {})
        cash = self._unformat(fund.get("cash"))
        operating_cf = self._unformat(fund.get("operating_cash_flow"))
        # Raw float (percent) or None - the balance-sheet growth/contraction
        # proxy used by _build_flags to refine the sector runway exemption.
        total_assets_yoy = self._unformat(fund.get("total_assets_yoy_change_pct"))
        # Whether a fixed burn-rate runway is a meaningful interpretation for
        # this company's sector. Carried on the runway dict so every consumer
        # (flags, summary text, the LLM financing note, the UI card) reads one
        # source of truth and none of them narrates a bank/insurer/REIT's
        # structural negative OCF as a cash-burn runway. Mirrors
        # RUNWAY_EXEMPT_SECTORS via the fundamentals sector flags.
        sector_exempt = bool(fund.get("is_financial_sector") or fund.get("is_reit"))

        if cash is None or operating_cf is None:
            return {"available": False, "sector_exempt": sector_exempt,
                    "total_assets_yoy_change_pct": total_assets_yoy}

        if operating_cf >= 0:
            return {
                "available": True,
                "cash": cash,
                "annual_operating_cash_flow": operating_cf,
                "cash_flow_positive": True,
                "runway_months": None,
                "sector_exempt": sector_exempt,
                "total_assets_yoy_change_pct": total_assets_yoy,
            }

        monthly_burn = abs(operating_cf) / 12
        runway_months = cash / monthly_burn if monthly_burn else None

        return {
            "available": True,
            "cash": cash,
            "annual_operating_cash_flow": operating_cf,
            "cash_flow_positive": False,
            "runway_months": runway_months,
            "sector_exempt": sector_exempt,
            "total_assets_yoy_change_pct": total_assets_yoy,
        }

    @staticmethod
    def _unformat(value) -> Optional[float]:
        """Parse a comma-formatted display string (or raw number) back to a float"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            cleaned = str(value).replace(",", "").strip()
            if not cleaned or cleaned.upper() == "N/A":
                return None
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def _build_flags(self, dilution: Dict[str, Any], runway: Dict[str, Any],
                      financing_filings: List[Dict[str, Any]],
                      company_info: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build risk-shaped flags from dilution, runway, and filing signals"""

        flags = []

        # ========== DILUTION ==========
        if dilution.get("available") and dilution.get("yoy_change_pct") is not None:
            yoy = dilution["yoy_change_pct"]
            if yoy >= 20:
                flags.append({
                    "title": "Rapid Share Dilution",
                    "category": "Financing",
                    "severity": "High",
                    "description": (
                        f"Shares outstanding grew {yoy:.1f}% year-over-year. Dilution of this "
                        "magnitude reduces each existing holder's claim on future earnings and "
                        "assets regardless of how the underlying business performs - a holder "
                        "who did not participate in the raise now owns a materially smaller "
                        "slice of the company. Sustained issuance at this pace can offset or "
                        "outweigh operational progress."
                    ),
                    "metric": f"{yoy:+.1f}% YoY",
                    "impact": "Per-share earnings and book value are eroded independent of operating results",
                })
            elif yoy >= 8:
                flags.append({
                    "title": "Elevated Share Dilution",
                    "category": "Financing",
                    "severity": "Medium",
                    "description": (
                        f"Shares outstanding grew {yoy:.1f}% year-over-year. This is a meaningful "
                        "increase in share count and worth monitoring - continued issuance at this "
                        "rate would compound into significant dilution for holders who don't "
                        "participate in future raises."
                    ),
                    "metric": f"{yoy:+.1f}% YoY",
                    "impact": "Ongoing issuance at this pace would gradually erode per-share value",
                })

        if dilution.get("likely_split"):
            direction = dilution.get("split_direction")
            confidence = dilution.get("split_confidence")

            if direction == "reverse":
                title = "Reverse Split — Dilution Trend Obscured"
                description = (
                    "A reverse stock split occurred within the lookback window, which "
                    "mechanically resets the share count and can mask an otherwise "
                    "aggressive dilution trend. Treat the raw share-count trend as "
                    "unreliable here and weight the financing filing list and cash "
                    "runway more heavily instead."
                )
                metric = "Reverse split detected"
                impact = "Underlying dilution pace may be understated by this metric alone"
            else:
                title = "Stock Split Detected — Share-Count Jump Is Not Dilution"
                description = (
                    "A forward stock split occurred within the lookback window, which "
                    "mechanically increases the share count without changing any "
                    "shareholder's proportional ownership. The share-count jump this "
                    "would otherwise register as dilution has been excluded from the "
                    "year-over-year/quarter-over-quarter readings above."
                )
                metric = "Forward split detected"
                impact = "No dilution occurred - share count increased, ownership percentage did not change"

            if confidence == "heuristic":
                description += (
                    " This was inferred from the size of the share-count change alone - "
                    "no confirming corporate-action data was available - so treat this "
                    "classification as lower-confidence."
                )

            flags.append({
                "title": title,
                "category": "Financing",
                "severity": "Medium",
                "description": description,
                "metric": metric,
                "impact": impact,
            })

        # ========== CASH RUNWAY ==========
        sector = (company_info or {}).get("sector", "")
        is_balance_sheet_driven = sector in RUNWAY_EXEMPT_SECTORS
        if runway.get("cash_flow_positive") is False:
            runway_months = runway.get("runway_months")
            total_assets_yoy = runway.get("total_assets_yoy_change_pct")

            if is_balance_sheet_driven:
                # Negative OCF is normally structural for these sectors (see
                # RUNWAY_EXEMPT_SECTORS), so the burn-rate runway flag is
                # suppressed - UNLESS the balance sheet is actually shrinking,
                # which is the opposite of funding growth and worth a distinct,
                # sector-appropriate flag (not framed as burn-rate insolvency).
                # When the trend proxy is unavailable, fall back to blanket
                # suppression rather than inventing a signal.
                if total_assets_yoy is not None and total_assets_yoy < BALANCE_SHEET_CONTRACTION_YOY_PCT:
                    flags.append({
                        "title": "Balance Sheet Contraction",
                        "category": "Financing",
                        "severity": "Medium",
                        "description": (
                            f"Total assets declined {abs(total_assets_yoy):.1f}% year-over-year "
                            "while operating cash flow was negative. For a bank, insurer, or REIT, "
                            "negative operating cash flow usually reflects funding balance-sheet "
                            "GROWTH and is not a liquidity-stress signal - but here the balance "
                            "sheet is contracting, not growing, the opposite pattern, which can "
                            "accompany deposit outflows, asset sales, or forced deleveraging. This "
                            "is deliberately not a burn-rate/runway estimate (that framing doesn't "
                            "fit a balance-sheet-driven business); it's a prompt to look at why the "
                            "balance sheet is shrinking."
                        ),
                        "metric": f"{total_assets_yoy:+.1f}% total assets YoY",
                        "impact": "Contraction alongside negative operating cash flow warrants review of deposit/funding trends",
                    })
                # else: growing or trend-unknown -> suppressed (benign case)
            elif runway_months is not None:
                if runway_months <= 6:
                    flags.append({
                        "title": "Limited Cash Runway",
                        "category": "Financing",
                        "severity": "High",
                        "description": (
                            f"At the current annualized operating cash burn, estimated runway is "
                            f"only ~{runway_months:.0f} months. This is an annualized estimate "
                            "derived from trailing operating cash flow - confirm against the "
                            "latest 10-Q for a more current read. Companies this close to "
                            "exhausting cash typically must raise capital soon, often on "
                            "unfavorable, dilutive terms."
                        ),
                        "metric": f"~{runway_months:.0f} months",
                        "impact": "Near-term financing is likely, raising the probability of a dilutive raise",
                    })
                elif runway_months <= 12:
                    flags.append({
                        "title": "Limited Cash Runway",
                        "category": "Financing",
                        "severity": "Medium",
                        "description": (
                            f"At the current annualized operating cash burn, estimated runway is "
                            f"~{runway_months:.0f} months. This is an annualized estimate derived "
                            "from trailing operating cash flow - confirm against the latest 10-Q "
                            "for a more current read. A raise within the next year is plausible if "
                            "burn does not improve."
                        ),
                        "metric": f"~{runway_months:.0f} months",
                        "impact": "A financing event within the next 12 months is plausible absent improved cash flow",
                    })

        # ========== FINANCING FILINGS ==========
        if financing_filings:
            distinct_forms = sorted({f.get("form", "Unknown") for f in financing_filings})
            count = len(financing_filings)
            severity = "High" if count >= 3 else "Medium"
            flags.append({
                "title": "Active Financing-Related Filings",
                "category": "Financing",
                "severity": severity,
                "description": (
                    f"{count} financing-related SEC filing(s) in the past ~18 months: "
                    f"{', '.join(distinct_forms)}. These filings (shelf registrations, "
                    "prospectus supplements, and 8-Ks disclosing material agreements or "
                    "unregistered equity sales) are how ATM programs, equity lines, and "
                    "PIPE-style financings actually get put in place and drawn on - their "
                    "presence signals active or imminent capital-raising activity that can "
                    "add supply to the float."
                ),
                "metric": f"{count} filing(s)",
                "impact": "Ongoing capacity to issue shares outside of normal operating cash flow needs",
            })

        # ========== MICRO-CAP CONTEXT ==========
        if flags:
            market_cap = (company_info or {}).get("market_cap")
            try:
                if market_cap is not None and float(market_cap) < 300_000_000:
                    flags[-1] = dict(flags[-1])
                    flags[-1]["description"] += (
                        " At this market capitalization, thinner institutional sponsorship "
                        "amplifies the impact of financing-driven share supply relative to a "
                        "large-cap issuer."
                    )
            except (TypeError, ValueError):
                pass

        return flags

    def _overhang_level(self, dilution: Dict[str, Any], runway: Dict[str, Any],
                         financing_filings: List[Dict[str, Any]],
                         company_info: Optional[Dict[str, Any]] = None) -> str:
        """Roll dilution, runway, and filing signals into a Low/Medium/High score"""

        score = 0

        # yoy_change_pct is None post-split until enough history accumulates,
        # so this intentionally contributes nothing - filing-count and
        # runway below carry the score instead.
        if dilution.get("available") and dilution.get("yoy_change_pct") is not None:
            yoy = dilution["yoy_change_pct"]
            if yoy >= 20:
                score += 2
            elif yoy >= 8:
                score += 1

        # Runway contributes to the score only where a burn-based runway is a
        # meaningful signal - gated out for the same balance-sheet-driven
        # sectors as the flag above, so a bank's structural negative OCF can't
        # inflate the overhang level either.
        sector = (company_info or {}).get("sector", "")
        runway_score_applicable = sector not in RUNWAY_EXEMPT_SECTORS
        if runway_score_applicable and runway.get("cash_flow_positive") is False:
            runway_months = runway.get("runway_months")
            if runway_months is not None:
                if runway_months <= 6:
                    score += 2
                elif runway_months <= 12:
                    score += 1

        if financing_filings:
            if len(financing_filings) >= 3:
                score += 2
            else:
                score += 1

        if score >= 4:
            return "High"
        elif score >= 2:
            return "Medium"
        else:
            return "Low"

    def _summarize(self, overhang_level: str, dilution: Dict[str, Any],
                    runway: Dict[str, Any], financing_filings: List[Dict[str, Any]]) -> str:
        """One-paragraph plain-English summary of financing/dilution overhang"""

        if dilution.get("available") and dilution.get("yoy_change_pct") is not None:
            dilution_text = f"shares outstanding have changed {dilution['yoy_change_pct']:+.1f}% year-over-year"
        else:
            dilution_text = "trailing share-count change is unavailable"

        if runway.get("available"):
            if runway.get("cash_flow_positive"):
                runway_text = "the company is cash-flow positive from operations, reducing near-term pressure to raise capital"
            elif runway.get("sector_exempt"):
                # Don't narrate a bank/insurer/REIT's structural negative OCF
                # as a burn-rate runway - that's the same misframing the flag
                # suppression removed. State the balance-sheet trend instead.
                ta_yoy = runway.get("total_assets_yoy_change_pct")
                if ta_yoy is not None and ta_yoy < 0:
                    runway_text = (
                        f"operating cash flow is negative while total assets shrank "
                        f"{abs(ta_yoy):.1f}% year-over-year - for a balance-sheet-driven business "
                        "that contraction, not a fixed cash-runway estimate, is the liquidity signal to watch"
                    )
                else:
                    runway_text = (
                        "operating cash flow is negative, which for a balance-sheet-driven business "
                        "(bank, insurer, or REIT) typically reflects funding asset growth rather than "
                        "cash burn, so a fixed cash-runway figure is not a meaningful measure here"
                    )
            elif runway.get("runway_months") is not None:
                runway_text = f"estimated cash runway is ~{runway['runway_months']:.0f} months at the current burn rate"
            else:
                runway_text = "cash runway could not be estimated"
        else:
            runway_text = "cash runway is unavailable due to missing fundamentals data"

        filing_count = len(financing_filings)
        if filing_count:
            filing_text = f"{filing_count} financing-related SEC filing(s) were identified in the past ~18 months"
        else:
            filing_text = "no financing-related SEC filings were identified in the past ~18 months"

        return (
            f"Financing & dilution overhang is assessed as {overhang_level}. "
            f"On the share count, {dilution_text}. On liquidity, {runway_text}. "
            f"On SEC activity, {filing_text}."
        )
