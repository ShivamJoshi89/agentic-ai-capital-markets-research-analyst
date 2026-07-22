"""
Report Generation Agent
Generates final investment research memo using OpenAI LLM.
"""

import logging
from typing import Dict, Any
import sys
from pathlib import Path
from openai import OpenAI

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import Config

logger = logging.getLogger(__name__)


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
YTD Return: {market_data.get('metrics', {}).get('ytd_return', 'N/A')}%
Volatility: {market_data.get('metrics', {}).get('volatility', 'N/A')}%
52-Week High: ${company_info.get('52_week_high', 'N/A')}
52-Week Low: ${company_info.get('52_week_low', 'N/A')}

FINANCIAL FUNDAMENTALS
----------------------
Revenue: {fundamentals.get('fundamentals', {}).get('revenue', 'N/A')}
Net Income: {fundamentals.get('fundamentals', {}).get('net_income', 'N/A')}
P/E Ratio: {fundamentals.get('fundamentals', {}).get('pe_ratio', 'N/A')}
Profit Margin: {fundamentals.get('fundamentals', {}).get('profit_margin', 'N/A')}
Debt-to-Equity: {fundamentals.get('fundamentals', {}).get('debt_to_equity', 'N/A')}
ROE: {fundamentals.get('fundamentals', {}).get('roe', 'N/A')}

NEWS & SENTIMENT
----------------
Overall Sentiment: {news_data.get('overall_sentiment', 'N/A')}
Total Articles Analyzed: {news_data.get('total_articles', 0)}

MACRO ENVIRONMENT
-----------------
Federal Funds Rate: {macro_data.get('indicators', {}).get('fed_rate', 'N/A')}
Inflation (CPI): {macro_data.get('indicators', {}).get('cpi_inflation', 'N/A')}
Unemployment: {macro_data.get('indicators', {}).get('unemployment_rate', 'N/A')}

KEY RISKS
---------
{self._format_risks(risk_data)}

COMPANY SUMMARY
---------------
{company_info.get('business_summary', 'N/A')[:500]}...
"""
        
        return context
    
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
                model="gpt-3.5-turbo",
                max_tokens=2000,
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