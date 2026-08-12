"""
Report Generation Agent
Generates final investment research memo using OpenAI LLM.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional
import sys
from pathlib import Path
from openai import OpenAI

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import Config

logger = logging.getLogger(__name__)

# Dedicated audit log for the exact context handed to the LLM, so any wrong
# or unsupported claim in a generated memo can be traced back to precisely
# what the model was given. Separate logger (not the noisy default one) so it
# can be routed/retained independently; emitted at DEBUG to stay out of normal
# INFO output while remaining capturable when traceability is needed.
audit_logger = logging.getLogger(f"{__name__}.audit")


class ReportAgent:
    """
    Responsible for generating the final investment research memo.
    
    Responsibilities:
    - Combine all agent outputs
    - Create executive summary
    - Structure bull/base/bear cases
    - Generate final recommendations
    - Format as professional memo
    """
    
    def __init__(self):
        """Initialize the Report Generation Agent"""
        self.name = "Report Generation Agent"
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        logger.info(f"{self.name} initialized")
    
    def run(self, ticker: str, all_agent_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate investment research memo.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'JPM')
            all_agent_outputs: Dictionary with outputs from all agents
        
        Returns:
            Dictionary with final investment memo
        """
        logger.info(f"Generating research memo for {ticker}")
        
        try:
            # Prepare data for LLM
            analysis_context = self._prepare_context(ticker, all_agent_outputs)

            # Persist the exact context handed to the model, before the call,
            # so a wrong/unsupported memo claim can be traced to its input.
            self._audit_log_context(ticker, analysis_context)

            # Generate memo using OpenAI
            company_name = all_agent_outputs.get("company_info", {}).get("company_name", ticker)
            memo = self._generate_memo_with_llm(ticker, analysis_context, company_name)
            
            return {
                "ticker": ticker,
                "success": True,
                "memo": memo,
                "timestamp": str(self._get_timestamp())
            }
        
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return {
                "ticker": ticker,
                "success": False,
                "error": str(e),
                "memo": self._generate_fallback_memo(ticker, all_agent_outputs)
            }
    
    def _prepare_context(self, ticker: str, all_outputs: Dict[str, Any]) -> str:
        """Prepare structured context for LLM"""
        
        company_info = all_outputs.get("company_info", {})
        market_data = all_outputs.get("market_data", {})
        fundamentals = all_outputs.get("fundamentals_data", {})
        news_data = all_outputs.get("news_data", {})
        macro_data = all_outputs.get("macro_data", {})
        risk_data = all_outputs.get("risk_data", {})
        financing_data = all_outputs.get("financing_data", {})

        # Abbreviate EVERY large dollar figure for the LLM (see
        # _format_large_number) so none reaches the model as a raw comma-
        # grouped digit string - a known magnitude-misreading risk. This is
        # the full balance-sheet/cash-flow set, not just Revenue/Net Income:
        # the Round 2 finding was about large dollar figures generally, with
        # revenue only the illustrative example. Total Liabilities is included
        # too (it completes Assets = Liabilities + Equity) even though it isn't
        # a headline figure. The already-human-readable ratio fields (P/E,
        # margins, D/E, ROE) are correctly left untouched below. All share the
        # single currency-aware prefix so they compose with the FX note.
        money_prefix = self._money_prefix(fundamentals)
        fund_metrics = fundamentals.get("fundamentals", {})

        def money(key):
            return self._format_large_number(fund_metrics.get(key), money_prefix)

        revenue_str = money("revenue")
        net_income_str = money("net_income")
        total_assets_str = money("total_assets")
        total_liabilities_str = money("total_liabilities")
        total_equity_str = money("total_equity")
        total_debt_str = money("total_debt")
        cash_str = money("cash")
        operating_cash_flow_str = money("operating_cash_flow")
        free_cash_flow_str = money("free_cash_flow")

        context = f"""
INVESTMENT RESEARCH MEMO PREPARATION
=====================================

Company: {company_info.get('company_name', ticker)}
Ticker: {ticker}
Sector: {company_info.get('sector', 'N/A')}
Industry: {company_info.get('industry', 'N/A')}

MARKET DATA
-----------
Current Price: ${market_data.get('metrics', {}).get('latest_price', 'N/A')}
{self._format_ytd_line(market_data)}
Volatility: {market_data.get('metrics', {}).get('volatility', 'N/A')}%
52-Week High: ${company_info.get('52_week_high', 'N/A')}
52-Week Low: ${company_info.get('52_week_low', 'N/A')}

FINANCIAL FUNDAMENTALS
----------------------
{self._format_currency_note(fundamentals)}Revenue: {revenue_str}
Net Income: {net_income_str}
Total Assets: {total_assets_str}
Total Liabilities: {total_liabilities_str}
Total Equity: {total_equity_str}
Total Debt: {total_debt_str}
Cash: {cash_str}
Operating Cash Flow: {operating_cash_flow_str}
Free Cash Flow: {free_cash_flow_str}
P/E Ratio: {fundamentals.get('fundamentals', {}).get('pe_ratio', 'N/A')}
Profit Margin: {fundamentals.get('fundamentals', {}).get('profit_margin', 'N/A')}
Debt-to-Equity: {fundamentals.get('fundamentals', {}).get('debt_to_equity', 'N/A')}
ROE: {fundamentals.get('fundamentals', {}).get('roe', 'N/A')}
{self._valuation_caveats(fundamentals)}
NEWS & SENTIMENT
----------------
Overall Sentiment: {news_data.get('overall_sentiment', 'N/A')}
Total Articles Analyzed: {news_data.get('total_articles', 0)}

MACRO ENVIRONMENT
-----------------
Federal Funds Rate: {macro_data.get('indicators', {}).get('fed_rate', 'N/A')}
Inflation (CPI): {macro_data.get('indicators', {}).get('cpi_inflation', 'N/A')}
Unemployment: {macro_data.get('indicators', {}).get('unemployment_rate', 'N/A')}

FINANCING & DILUTION RISK
--------------------------
{self._format_financing(financing_data)}

KEY RISKS
---------
{self._format_risks(risk_data)}

COMPANY SUMMARY
---------------
{company_info.get('business_summary', 'N/A')[:500]}...
"""
        
        return context
    
    @staticmethod
    def _audit_log_context(ticker: str, context: str) -> None:
        """Emit the full LLM context to the audit log with ticker + timestamp.
        DEBUG level: capturable for traceability without cluttering normal
        output."""
        audit_logger.debug(
            "LLM_CONTEXT ticker=%s timestamp=%s\n%s",
            ticker, datetime.now().isoformat(), context,
        )

    @staticmethod
    def _parse_numeric(value: Any) -> Optional[float]:
        """Parse a number out of a formatted display string
        ("466,822,987,776", "24.00%", "1.54x", "$347.28") or a raw number.
        Mirrors the frontend's parseNumeric. Returns None for N/A / non-
        numeric so the caller can render "N/A" rather than a spurious 0."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        cleaned = re.sub(r"[$%x,\s]", "", str(value))
        if cleaned == "" or cleaned.upper().startswith("N/A"):
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _format_large_number(value: Any, prefix: str = "$") -> str:
        """Python port of the frontend's formatLargeNumber: 922665484288 ->
        "$922.7B". Large dollar figures were previously interpolated into the
        LLM prompt as raw comma-grouped 12-digit strings ("466,822,987,776"),
        a known magnitude-misreading risk for language models; abbreviating
        keeps the scale unambiguous. `prefix` is "$" for USD and "" for a
        foreign issuer's un-converted native-currency figures (the currency
        note already discloses which currency those are in)."""
        n = ReportAgent._parse_numeric(value)
        if n is None:
            return "N/A"
        a = abs(n)
        if a >= 1e12:
            return f"{prefix}{n / 1e12:.2f}T"
        if a >= 1e9:
            return f"{prefix}{n / 1e9:.1f}B"
        if a >= 1e6:
            return f"{prefix}{n / 1e6:.1f}M"
        if a >= 1e3:
            return f"{prefix}{n / 1e3:.1f}K"
        return f"{prefix}{n:.2f}"

    @staticmethod
    def _money_prefix(fundamentals_data: Dict[str, Any]) -> str:
        """"$" for USD-denominated figures (the normal case, and after FX
        conversion), "" for a foreign issuer's figures left in their native
        currency because no USD rate was available - in which case the
        currency note above the figures states the currency, so prepending a
        "$" would misstate them. Composes with _format_currency_note without
        duplicating or contradicting its disclosure."""
        fx = fundamentals_data.get("fundamentals", {}).get("fx_conversion") or {}
        if fx.get("applied"):
            return "$"  # converted to USD
        native = fx.get("native_currency")
        if native and native != "USD":
            return ""  # native, non-USD - currency note discloses which
        return "$"

    @staticmethod
    def _format_ytd_line(market_data: Dict[str, Any]) -> str:
        """Label the return figure by its actual basis so the LLM never
        narrates a since-inception (early-January fallback) figure as a
        calendar-YTD return. market_data_agent computes ytd_return as a true
        calendar-YTD in the normal case and flags the fallback via
        ytd_basis."""
        metrics = market_data.get("metrics", {})
        value = metrics.get("ytd_return", "N/A")
        if metrics.get("ytd_basis") == "trailing_since_series_start":
            return f"Return (trailing since series start - no calendar-YTD base available yet): {value}%"
        return f"YTD Return: {value}%"

    @staticmethod
    def _valuation_caveats(fundamentals_data: Dict[str, Any]) -> str:
        """Sector/valuation caveats mirroring the risk-layer suppressions and
        the UI's own disclaimers, so the LLM reflects them instead of re-
        deriving the framing they exist to prevent. Evidence: when a REIT's
        raw GAAP 'P/E Ratio: 45.28' was passed in with no caveat, both models
        editorialized it as a 'premium valuation' - undoing the risk agent's
        REIT P/E suppression in the generated memo. Returns "" for an ordinary
        company (no caveats), else a block ending in "\\n"."""
        f = fundamentals_data.get("fundamentals", {})
        notes = []
        if f.get("is_reit"):
            notes.append(
                "- REIT: GAAP net income (hence the P/E and profit margin above) is depressed by "
                "large non-cash real-estate depreciation. REITs are valued on FFO/AFFO, which is "
                "NOT provided here - do not describe the GAAP P/E as simply 'expensive' or a "
                "'premium valuation' without this caveat."
            )
        if f.get("is_financial_sector"):
            notes.append(
                "- Bank/insurer: gross margin and current/quick ratios are not meaningful (shown "
                "N/A); operating cash flow is dominated by lending/reserve flows, not cash burn."
            )
        if f.get("negative_equity"):
            notes.append(
                "- Negative shareholders' equity: ROE, P/B, and D/E are not meaningful (shown N/A) "
                "- do not infer a return on equity or a book-value multiple from them."
            )
        # Data-quality provenance: gross/operating margin fell back to Yahoo's
        # precomputed value (the income statement couldn't support a local
        # recompute), which the audit found unreliable for some filers - flag
        # it so the memo doesn't lean on a possibly-wrong margin.
        margin_unverified = (
            (f.get("gross_margin_basis") == "info_fallback" and f.get("gross_margin") not in (None, "N/A"))
            or (f.get("operating_margin_basis") == "info_fallback" and f.get("operating_margin") not in (None, "N/A"))
        )
        if margin_unverified:
            notes.append(
                "- Gross/operating margin here is Yahoo's precomputed value (could not be recomputed "
                "from this filer's income statement) and may be unreliable - do not over-rely on it."
            )
        if not notes:
            return ""
        return "SECTOR/VALUATION CAVEATS (reflect these; do not contradict them):\n" + "\n".join(notes) + "\n"

    def _format_risks(self, risk_data: Dict[str, Any]) -> str:
        """Format risks for context"""
        
        risks = risk_data.get("risks", [])
        
        if not risks:
            return "No major risks identified."
        
        formatted = ""
        for i, risk in enumerate(risks[:5], 1):  # Top 5 risks
            formatted += f"\n{i}. {risk.get('title')} ({risk.get('severity')})\n"
            formatted += f"   {risk.get('description')}\n"
        
        return formatted

    @staticmethod
    def _format_currency_note(fundamentals_data: Dict[str, Any]) -> str:
        """Currency disclosure line for the FINANCIAL FUNDAMENTALS section -
        empty string for an ordinary USD reporter, otherwise a line stating
        what currency the figures below are actually in (and, if converted,
        the rate used), so the LLM never narrates a foreign issuer's
        figures as USD amounts. Returns a string ending in "\\n" (or "")
        so it can be interpolated directly above the Revenue/Net Income
        lines without an extra blank line in the normal USD case.
        """
        fx = fundamentals_data.get("fundamentals", {}).get("fx_conversion") or {}
        if fx.get("applied"):
            rate = fx.get("rate")
            rate_str = f"{rate:.6g}" if isinstance(rate, (int, float)) else rate
            return (
                f"(Converted from {fx.get('from_currency')} to {fx.get('to_currency')} "
                f"at {rate_str} as of {fx.get('rate_as_of')})\n"
            )
        native = fx.get("native_currency")
        if native and native != "USD":
            return f"(Figures below are in {native} - no USD conversion rate was available)\n"
        return ""

    def _format_financing(self, financing_data: Dict[str, Any]) -> str:
        """Format financing/dilution data for LLM context"""
        if not financing_data or not financing_data.get("success"):
            return "Financing/dilution data unavailable."

        lines = [f"Overhang Level: {financing_data.get('overhang_level', 'Unknown')}"]

        dilution = financing_data.get("dilution", {})
        if dilution.get("available") and dilution.get("yoy_change_pct") is not None:
            lines.append(f"Shares Outstanding YoY Change: {dilution['yoy_change_pct']:+.1f}%")

        runway = financing_data.get("cash_runway", {})
        if runway.get("available"):
            if runway.get("cash_flow_positive"):
                lines.append("Cash Flow: Positive (no burn-driven raise pressure)")
            elif runway.get("sector_exempt"):
                # Don't hand the LLM a burn-rate runway for a bank/insurer/REIT
                # (structural negative OCF, not cash burn) - state the balance-
                # sheet trend instead so the memo can't narrate false runway.
                ta_yoy = runway.get("total_assets_yoy_change_pct")
                if ta_yoy is not None and ta_yoy < 0:
                    lines.append(
                        f"Operating Cash Flow: Negative with total assets down {abs(ta_yoy):.1f}% YoY "
                        "(balance-sheet contraction; a fixed cash-runway figure is not meaningful for this sector)"
                    )
                else:
                    lines.append(
                        "Operating Cash Flow: Negative (structural for a balance-sheet-driven business; "
                        "not a cash-burn/runway signal)"
                    )
            elif runway.get("runway_months") is not None:
                lines.append(f"Estimated Cash Runway: ~{runway['runway_months']:.0f} months")

        filings = financing_data.get("financing_filings", [])
        if filings:
            lines.append(f"Recent Financing-Related SEC Filings: {len(filings)} in past ~18 months")

        return "\n".join(lines)

    # Memo model. Chosen over the previous gpt-3.5-turbo baseline on an
    # 8-ticker faithfulness comparison (AAPL/JPM/O/PGR/MRNA/DPZ/TM/NVO): the
    # newer model reproduced the input revenue magnitude in 8/8 memos vs 4/8
    # for gpt-3.5-turbo, correctly narrated N/A ratios ("ROE is not meaningful
    # with negative equity") rather than inventing figures, and produced more
    # sector-aware, better-hedged prose. Per-memo cost is ~$0.006 standard /
    # ~$0.003 Batch (memo generation is not real-time, so Batch applies) - a
    # few tenths of a cent, immaterial for this tool. gpt-5.x models require
    # max_completion_tokens (not max_tokens) and reserve part of that budget
    # for reasoning tokens, so the limit is set generously to avoid truncation.
    LLM_MODEL = "gpt-5.4-mini"
    LLM_MAX_COMPLETION_TOKENS = 4000

    PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent / "prompts" / "research_memo_prompt.txt"

    def _load_prompt_template(self) -> str:
        """Load the memo prompt template, or None if unavailable"""
        try:
            return self.PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning(f"Could not load research_memo_prompt.txt ({e}), using built-in prompt")
            return None

    def _generate_memo_with_llm(self, ticker: str, context: str, company_name: str = "") -> str:
        """Generate memo using OpenAI, driven by the prompt template file"""

        template = self._load_prompt_template()
        if template:
            # .replace() rather than .format() so literal braces in the
            # template can never raise KeyError
            prompt = (
                template
                .replace("{ticker}", ticker)
                .replace("{company_name}", company_name or ticker)
                .replace("{analysis_context}", context)
            )
        else:
            prompt = self._build_fallback_prompt(ticker, context)

        try:
            response = self.client.chat.completions.create(
                model=self.LLM_MODEL,
                max_completion_tokens=self.LLM_MAX_COMPLETION_TOKENS,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    @staticmethod
    def _build_fallback_prompt(ticker: str, context: str) -> str:
        """Built-in prompt used only if the template file is missing"""

        return f"""You are a professional investment analyst. Based on the following research data,
write a comprehensive investment research memo for {ticker}.

{context}

Generate a professional investment memo with the following sections:

1. EXECUTIVE SUMMARY
   - Brief overview of the investment case
   - Key metrics snapshot

2. COMPANY OVERVIEW
   - Business description
   - Competitive position
   - Market opportunity

3. FINANCIAL ANALYSIS
   - Key financial metrics and trends
   - Profitability and efficiency analysis
   - Balance sheet strength

4. MARKET PERFORMANCE
   - Recent stock performance
   - Volatility and risk metrics
   - Technical position

5. KEY RISKS
   - Most significant risks
   - Mitigation factors
   - Downside scenarios

6. BULL CASE
   - Growth catalysts
   - Valuation upside
   - Market opportunity expansion

7. BASE CASE
   - Expected scenario (most likely)
   - Valuation metrics
   - Earnings trajectory

8. BEAR CASE
   - Downside risks
   - Valuation compression
   - Earnings decline scenarios

9. INVESTMENT RECOMMENDATION
   - Summary rating
   - Key reasons for rating
   - Risk/reward assessment

10. DISCLAIMER
    - Standard legal disclaimers
    - Information sources
    - Limitations

Write in professional analyst style. Be balanced and data-driven. Include specific numbers and metrics.
Avoid making definitive buy/sell recommendations - focus on analysis and risks.
"""

    def _generate_fallback_memo(self, ticker: str, all_outputs: Dict[str, Any]) -> str:
        """Generate fallback memo if LLM fails"""
        
        company_info = all_outputs.get("company_info", {})
        market_data = all_outputs.get("market_data", {})
        fundamentals = all_outputs.get("fundamentals_data", {})
        risk_data = all_outputs.get("risk_data", {})
        
        memo = f"""
INVESTMENT RESEARCH MEMO
{ticker} - {company_info.get('company_name', 'N/A')}

EXECUTIVE SUMMARY
The analysis of {ticker} reveals a complex investment profile with both opportunities and risks.
Current price: ${market_data.get('metrics', {}).get('latest_price', 'N/A')}
YTD Performance: {market_data.get('metrics', {}).get('ytd_return', 'N/A')}%

FINANCIAL METRICS
Revenue: {fundamentals.get('fundamentals', {}).get('revenue', 'N/A')}
P/E Ratio: {fundamentals.get('fundamentals', {}).get('pe_ratio', 'N/A')}
Profit Margin: {fundamentals.get('fundamentals', {}).get('profit_margin', 'N/A')}

KEY RISKS IDENTIFIED
{risk_data.get('summary', 'Multiple risks identified')}

BULL CASE
- Strong market position
- Solid financial fundamentals
- Potential for earnings growth

BASE CASE
- Stable operations
- Market-competitive valuation
- Modest earnings growth

BEAR CASE
- Economic slowdown could impact earnings
- Valuation may be at risk if rates rise
- Competitive pressures in sector

DISCLAIMER
This analysis is for educational purposes only. Not investment advice.
Consult with a financial advisor before making investment decisions.
"""
        
        return memo
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()