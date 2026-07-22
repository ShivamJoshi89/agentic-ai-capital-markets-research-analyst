"""
Risk Agent - IMPROVED VERSION
Identifies and analyzes key risks affecting a company and stock.
"""

import logging
from typing import Dict, Any, List
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class RiskAgent:
    """
    Responsible for identifying and analyzing key risks.
    
    Responsibilities:
    - Identify company-specific risks from fundamentals
    - Identify market and valuation risks
    - Identify macro risks with company context
    - Explain risk severity and impact
    """
    
    def __init__(self):
        """Initialize the Risk Agent"""
        self.name = "Risk Agent"
        logger.info(f"{self.name} initialized")
    
    def run(self, ticker: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify and analyze key risks.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'JPM')
            analysis_data: Aggregated analysis data from other agents
        
        Returns:
            Dictionary with identified risks
        """
        logger.info(f"Analyzing risks for {ticker}")
        
        try:
            # Extract data from agents
            market_data = analysis_data.get("market_data", {})
            fundamentals = analysis_data.get("fundamentals_data", {})
            news_data = analysis_data.get("news_data", {})
            company_info = analysis_data.get("company_info", {})
            macro_data = analysis_data.get("macro_data", {})
            
            # Identify risks with better analysis
            risks = self._identify_risks(
                ticker,
                market_data,
                fundamentals,
                news_data,
                company_info,
                macro_data
            )
            
            # Score and rank risks
            ranked_risks = self._rank_risks(risks)
            
            # Generate risk summary
            risk_summary = self._generate_risk_summary(ranked_risks)
            
            return {
                "ticker": ticker,
                "success": True,
                "risks": ranked_risks,
                "summary": risk_summary,
                "total_risks": len(ranked_risks)
            }
        
        except Exception as e:
            logger.error(f"Error analyzing risks: {str(e)}")
            return {
                "ticker": ticker,
                "success": False,
                "error": str(e),
                "risks": []
            }
    
    def _identify_risks(self, ticker, market_data, fundamentals, news_data, company_info, macro_data) -> List[Dict[str, Any]]:
        """Identify risks from all data sources"""
        
        risks = []
        
        # ========== VALUATION RISKS ==========
        if fundamentals.get("fundamentals"):
            fund = fundamentals.get("fundamentals", {})
            
            # High P/E ratio
            pe_str = str(fund.get("pe_ratio", "N/A")).replace("x", "").replace(",", "")
            try:
                pe = float(pe_str)
                if pe > 20:
                    risks.append({
                        "title": "Premium Valuation Multiple",
                        "category": "Valuation",
                        "severity": "High" if pe > 25 else "Medium",
                        "description": f"P/E ratio of {pe:.1f}x is elevated above historical averages. This limits margin of safety and suggests limited upside if earnings disappoint. Stock assumes significant earnings growth to justify current valuation.",
                        "metric": f"{pe:.1f}x",
                        "impact": "Negative earnings surprise could lead to significant valuation compression"
                    })
            except:
                pass
            
            # High P/B ratio
            pb_str = str(fund.get("pb_ratio", "N/A")).replace("x", "").replace(",", "")
            try:
                pb = float(pb_str)
                if pb > 3:
                    risks.append({
                        "title": "High Price-to-Book Ratio",
                        "category": "Valuation",
                        "severity": "Medium",
                        "description": f"P/B ratio of {pb:.1f}x indicates stock trades at significant premium to book value. This suggests market is pricing in substantial intangible value. Any deterioration in ROE or tangible assets could trigger repricing.",
                        "metric": f"{pb:.1f}x",
                        "impact": "Asset write-downs or ROE compression could be material"
                    })
            except:
                pass
        
        # ========== LEVERAGE & SOLVENCY RISKS ==========
        if fundamentals.get("fundamentals"):
            fund = fundamentals.get("fundamentals", {})
            
            # High debt
            debt_str = str(fund.get("debt_to_equity", "N/A")).replace("x", "").replace(",", "")
            try:
                de = float(debt_str)
                if de > 1.5:
                    risks.append({
                        "title": "High Financial Leverage",
                        "category": "Leverage",
                        "severity": "High",
                        "description": f"Debt-to-Equity ratio of {de:.2f}x indicates significant financial leverage. Company is highly leveraged relative to equity base. Rising interest rates or credit tightening could materially impact profitability. Limited financial flexibility in downturns.",
                        "metric": f"{de:.2f}x",
                        "impact": "Economic downturn could stress debt servicing ability"
                    })
                elif de > 1.0:
                    risks.append({
                        "title": "Elevated Debt Levels",
                        "category": "Leverage",
                        "severity": "Medium",
                        "description": f"Debt-to-Equity ratio of {de:.2f}x shows moderate leverage. While manageable, limits financial flexibility and increases vulnerability to interest rate spikes or credit market disruptions.",
                        "metric": f"{de:.2f}x",
                        "impact": "Rising rates could pressure earnings and cash flow"
                    })
            except:
                pass
        
        # ========== PROFITABILITY & MARGIN RISKS ==========
        if fundamentals.get("fundamentals"):
            fund = fundamentals.get("fundamentals", {})
            
            # Low or negative margins
            pm_str = str(fund.get("profit_margin", "N/A")).replace("%", "").replace(",", "")
            try:
                pm = float(pm_str)
                if pm < 5:
                    risks.append({
                        "title": "Thin Profit Margins",
                        "category": "Profitability",
                        "severity": "Medium",
                        "description": f"Profit margin of only {pm:.1f}% leaves limited room for error. Small revenue declines or cost increases can quickly erode profitability. Limited pricing power suggests competitive intensity.",
                        "metric": f"{pm:.1f}%",
                        "impact": "Revenue decline could result in significant earnings contraction"
                    })
            except:
                pass
        
        # ========== MARKET & VOLATILITY RISKS ==========
        if market_data.get("metrics"):
            metrics = market_data.get("metrics", {})
            
            # High volatility
            volatility = metrics.get("volatility", 0)
            if volatility and volatility > 25:
                risks.append({
                    "title": "Elevated Price Volatility",
                    "category": "Market",
                    "severity": "Medium" if volatility < 35 else "High",
                    "description": f"Stock volatility of {volatility:.1f}% is significantly higher than market average. Indicates high sensitivity to sentiment shifts and sector rotations. Investors face substantial intra-year drawdowns.",
                    "metric": f"{volatility:.1f}%",
                    "impact": "Could see sharp 15-20%+ drawdowns during market corrections"
                })
            
            # Large recent drawdown (max_drawdown is expressed in percent, e.g. -15.2)
            max_dd = metrics.get("max_drawdown", 0)
            if max_dd and max_dd < -25:
                risks.append({
                    "title": "Significant Recent Drawdown",
                    "category": "Market",
                    "severity": "High",
                    "description": f"Stock experienced {abs(max_dd):.1f}% peak-to-trough drawdown within past year. Suggests either sector weakness or company-specific deterioration. May indicate elevated vulnerability to further downside.",
                    "metric": f"{max_dd:.1f}%",
                    "impact": "Risk of additional 10-15% downside if momentum reverses"
                })
        
        # ========== MACRO & INTEREST RATE RISKS ==========
        if macro_data.get("success"):
            indicators = macro_data.get("indicators", {})
            
            # Interest rate environment
            fed_rate = str(indicators.get("fed_rate", ""))
            if "5" in fed_rate or ("4" in fed_rate and "75" in fed_rate):
                risks.append({
                    "title": "Interest Rate Vulnerability",
                    "category": "Macro",
                    "severity": "High",
                    "description": f"Federal funds rate at elevated levels ({fed_rate}). High rate environment pressures valuations through higher discount rates. Impacts borrowing costs and consumer spending. Extended high-rate regime could slow economic growth.",
                    "metric": fed_rate,
                    "impact": "Could result in 10-20% valuation compression if rates persist"
                })
            elif "4" in fed_rate:
                risks.append({
                    "title": "Persistent Higher Rates",
                    "category": "Macro",
                    "severity": "Medium",
                    "description": f"Rates remain elevated at {fed_rate}. This is constraining for growth stocks and companies with debt. Any attempts to raise rates further could be damaging.",
                    "metric": fed_rate,
                    "impact": "Additional rate hikes would negatively pressure valuations"
                })
            
            # Inflation
            inflation = str(indicators.get("cpi_inflation", ""))
            if "3" in inflation or "4" in inflation:
                risks.append({
                    "title": "Inflation & Margin Pressure",
                    "category": "Macro",
                    "severity": "Medium",
                    "description": f"Inflation at {inflation} remains sticky. Creates headwinds for labor costs and input prices. Companies with weak pricing power will face margin compression. May prompt additional rate hikes.",
                    "metric": inflation,
                    "impact": "Could pressure profit margins by 50-100bps"
                })
        
        # ========== NEWS & SENTIMENT RISKS ==========
        if news_data.get("success"):
            sentiment = news_data.get("overall_sentiment", "Neutral")
            if sentiment == "Negative":
                risks.append({
                    "title": "Negative News Sentiment",
                    "category": "Sentiment",
                    "severity": "Medium",
                    "description": "Recent news coverage is predominantly negative. Market sentiment toward the company/sector is bearish. Suggests investors are concerned about near-term catalysts or company execution.",
                    "metric": sentiment,
                    "impact": "Could lead to further downside until sentiment improves"
                })
        
        # ========== SECTOR-SPECIFIC RISKS ==========
        sector = company_info.get("sector", "")
        if sector:
            sector_risks = self._get_sector_risks(sector, company_info.get("company_name", ""))
            risks.extend(sector_risks)
        
        return risks
    
    def _get_sector_risks(self, sector: str, company_name: str) -> List[Dict[str, Any]]:
        """Get sector-specific risks with more depth"""
        
        sector_risks = {
            "Financial Services": [
                {
                    "title": "Interest Rate Sensitivity",
                    "category": "Sector",
                    "severity": "High",
                    "description": f"{company_name} is highly sensitive to interest rate movements. Margin compression in low-rate environments, but also vulnerable to rapid rate hikes. Net interest margin depends critically on yield curve slope.",
                    "metric": "Core business exposure",
                    "impact": "100bps rate change could impact NII by 2-5%"
                },
                {
                    "title": "Credit Cycle Risk",
                    "category": "Sector",
                    "severity": "High",
                    "description": "Financial institutions are pro-cyclical. Economic slowdown increases loan losses and credit impairments. Late-cycle deterioration could be sharp and sudden.",
                    "metric": "Economic sensitivity",
                    "impact": "Recession could cause loan losses to spike 50-100%"
                }
            ],
            "Technology": [
                {
                    "title": "Regulatory & Antitrust Risk",
                    "category": "Sector",
                    "severity": "High",
                    "description": f"{company_name} faces increasing regulatory scrutiny on data privacy, antitrust, and AI. Potential forced divestitures or operational restrictions could materially impact business model.",
                    "metric": "Regulatory exposure",
                    "impact": "Regulation could reduce addressable market by 10-30%"
                },
                {
                    "title": "Intense Competition",
                    "category": "Sector",
                    "severity": "High",
                    "description": "Tech sector features rapid innovation and low switching costs. Market leadership can be disrupted quickly. Customer acquisition costs rising as competition intensifies.",
                    "metric": "Competitive intensity",
                    "impact": "Loss of market position could result in 20-40% revenue decline"
                }
            ],
            "Healthcare": [
                {
                    "title": "Pricing & Regulatory Risk",
                    "category": "Sector",
                    "severity": "High",
                    "description": f"{company_name} operates in heavily regulated environment. Drug price controls, reimbursement pressure, and legislative changes pose significant profit risks.",
                    "metric": "Regulatory sensitivity",
                    "impact": "Price controls could reduce margins by 15-25%"
                }
            ],
            "Energy": [
                {
                    "title": "Commodity Price Volatility",
                    "category": "Sector",
                    "severity": "High",
                    "description": f"{company_name} earnings are highly dependent on volatile commodity prices. Operational leverage amplifies price movements. No hedging provides direct exposure.",
                    "metric": "Price sensitivity",
                    "impact": "$10/barrel oil price change = 10%+ earnings swing"
                }
            ]
        }
        
        return sector_risks.get(sector, [])
    
    def _rank_risks(self, risks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank risks by severity"""
        
        severity_order = {"High": 0, "Medium": 1, "Low": 2}
        
        sorted_risks = sorted(
            risks,
            key=lambda x: severity_order.get(x.get("severity", "Low"), 2)
        )
        
        return sorted_risks[:8]  # Return top 8 risks
    
    def _generate_risk_summary(self, risks: List[Dict[str, Any]]) -> str:
        """Generate comprehensive risk summary"""
        
        if not risks:
            return "No significant risks identified."
        
        high_severity = sum(1 for r in risks if r.get("severity") == "High")
        medium_severity = sum(1 for r in risks if r.get("severity") == "Medium")
        total = len(risks)
        
        summary = f"Identified {total} key risks: {high_severity} High severity, {medium_severity} Medium severity.\n\n"
        
        if high_severity >= 2:
            summary += "⚠️ SIGNIFICANT CONCERNS: Multiple high-severity risks warrant careful monitoring and potential position sizing reduction.\n"
        elif high_severity == 1:
            summary += "⚠️ ELEVATED RISK: One material risk factor identified that could significantly impact the investment thesis.\n"
        else:
            summary += "✓ Risk profile appears manageable with appropriate position sizing.\n"
        
        summary += "\nKey risk drivers by category:\n"
        categories = {}
        for risk in risks[:5]:
            cat = risk.get("category", "Other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(risk.get("title", "Unknown"))
        
        for cat, titles in categories.items():
            summary += f"• {cat}: {', '.join(titles)}\n"
        
        return summary