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

# Special-situation signals scanned for in news headlines. Keywords are
# matched case-insensitively; each category fires at most once per headline.
SPECIAL_SITUATION_PATTERNS = [
    {
        "category": "Activist Investor",
        "signal_type": "opportunity_signal",
        "keywords": ["activist investor", "activist stake", "activist fund",
                     "activist campaign", "activist pressure", "board seat"],
    },
    {
        "category": "M&A / Acquisition",
        "signal_type": "opportunity_signal",
        "keywords": ["merger", "acquisition", "acquires", "to acquire", "takeover",
                     "buyout", "deal talks", "bid for", "combination with"],
    },
    {
        "category": "Insider Buying",
        "signal_type": "opportunity_signal",
        "keywords": ["insider buying", "insider buys", "insider purchase",
                     "ceo buys", "director buys", "executives buy"],
    },
    {
        "category": "Insider Selling",
        "signal_type": "risk_signal",
        "keywords": ["insider selling", "insider sells", "insider sale",
                     "ceo sells", "director sells", "executives sell"],
    },
    {
        "category": "Earnings Beat",
        "signal_type": "opportunity_signal",
        "keywords": ["earnings beat", "beats earnings", "beats estimates",
                     "tops estimates", "beat expectations", "beats expectations",
                     "record quarter", "raises guidance"],
    },
    {
        "category": "Earnings Miss",
        "signal_type": "risk_signal",
        "keywords": ["earnings miss", "misses earnings", "misses estimates",
                     "missed estimates", "missed expectations", "falls short of estimates",
                     "cuts guidance", "lowers guidance", "profit warning"],
    },
    {
        "category": "Regulatory Catalyst (Positive)",
        "signal_type": "opportunity_signal",
        "keywords": ["fda approval", "fda approves", "fda clearance",
                     "regulatory approval", "wins approval", "cleared by regulators"],
    },
    {
        "category": "Regulatory Catalyst (Negative)",
        "signal_type": "risk_signal",
        "keywords": ["fda rejection", "fda declines", "regulatory probe",
                     "regulatory scrutiny", "sec investigation", "sec probe",
                     "doj investigation", "antitrust", "lawsuit", "fined"],
    },
    {
        "category": "Spin-off / Restructuring",
        "signal_type": "opportunity_signal",
        "keywords": ["spin-off", "spinoff", "spin off", "restructuring",
                     "divestiture", "carve-out", "carve out", "breakup", "break-up"],
    },
    {
        "category": "Share Buyback",
        "signal_type": "opportunity_signal",
        "keywords": ["buyback", "share repurchase", "repurchase program",
                     "repurchase plan", "repurchase authorization"],
    },
    {
        "category": "Dilutive Financing",
        "signal_type": "risk_signal",
        "keywords": ["common stock purchase agreement", "equity line of credit",
                     "committed equity facility", "at-the-market offering",
                     "atm offering", "shelf registration", "registered direct offering",
                     "convertible note financing", "dilutive financing",
                     "stock purchase agreement", "private placement"],
    },
]


class RiskAgent:
    """
    Responsible for identifying and analyzing key risks.
    
    Responsibilities:
    - Identify company-specific risks from fundamentals
    - Identify market and valuation risks
    - Identify macro risks with company context
    - Fold in financing/dilution overhang flags from the Financing Risk Agent
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
            financing_data = analysis_data.get("financing_data", {})

            # Identify risks with better analysis
            risks = self._identify_risks(
                ticker,
                market_data,
                fundamentals,
                news_data,
                company_info,
                macro_data
            )
            risks.extend(financing_data.get("flags", []))

            # Score and rank risks
            ranked_risks = self._rank_risks(risks)
            
            # Generate risk summary
            risk_summary = self._generate_risk_summary(ranked_risks)

            # Scan headlines for special situations (family office use case)
            special_situations = self.detect_special_situations(news_data.get("articles", []))

            return {
                "ticker": ticker,
                "success": True,
                "risks": ranked_risks,
                "summary": risk_summary,
                "total_risks": len(ranked_risks),
                "special_situations": special_situations
            }

        except Exception as e:
            logger.error(f"Error analyzing risks: {str(e)}")
            return {
                "ticker": ticker,
                "success": False,
                "error": str(e),
                "risks": [],
                "special_situations": []
            }

    def detect_special_situations(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scan news headlines for special-situation signals: activist involvement,
        M&A rumors, insider activity, earnings surprises, regulatory catalysts,
        spin-offs/restructurings, and share buybacks.

        Args:
            articles: News articles as returned by the News Agent

        Returns:
            List of flags, each with signal_type ("opportunity_signal" or
            "risk_signal"), category, matched keyword, and the headline
        """
        flags = []

        for article in articles or []:
            headline = article.get("title", "")
            if not headline:
                continue
            text = headline.lower()

            for pattern in SPECIAL_SITUATION_PATTERNS:
                matched = next((kw for kw in pattern["keywords"] if kw in text), None)
                if matched:
                    flags.append({
                        "signal_type": pattern["signal_type"],
                        "category": pattern["category"],
                        "matched_keyword": matched,
                        "headline": headline,
                        "url": article.get("url", ""),
                        "published_date": article.get("published_date", ""),
                    })

        if flags:
            logger.info(f"Detected {len(flags)} special situation signal(s) in headlines")

        return flags
    
    def _identify_risks(self, ticker, market_data, fundamentals, news_data, company_info, macro_data) -> List[Dict[str, Any]]:
        """Identify risks from all data sources"""
        
        risks = []
        
        # ========== VALUATION RISKS ==========
        if fundamentals.get("fundamentals"):
            fund = fundamentals.get("fundamentals", {})

            # REITs report GAAP net income that is structurally depressed by
            # large non-cash real-estate depreciation, so their GAAP P/E reads
            # far more "expensive" than the FFO/AFFO multiples the sector is
            # actually valued on. Applying the generic >20x premium-valuation
            # flag to a REIT would fire on almost every REIT purely as an
            # artifact of GAAP depreciation, so the P/E-based flag is
            # suppressed here (this pipeline doesn't compute FFO/AFFO; the UI
            # surfaces that caveat for the sector instead).
            is_reit = bool(fund.get("is_reit")) or company_info.get("sector") == "Real Estate"

            # High P/E ratio
            pe_str = str(fund.get("pe_ratio", "N/A")).replace("x", "").replace(",", "")
            try:
                pe = float(pe_str)
                if pe > 20 and not is_reit:
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

            # Negative shareholders' equity is a distinct, more serious
            # condition than "high leverage" - checked separately (and
            # first) because debt_to_equity renders as a non-numeric
            # "N/A (negative equity)" string in this case, which the
            # High Financial Leverage check below can't parse as a number
            # and would otherwise silently skip via its bare except.
            if fund.get("negative_equity"):
                risks.append({
                    "title": "Negative Shareholders' Equity",
                    "category": "Leverage",
                    "severity": "High",
                    "description": "Total liabilities exceed total assets, giving the company negative book equity. This typically results from sustained leveraged buybacks or accumulated losses funded by debt, and leaves no equity cushion to absorb further losses. Debt-to-Equity and Price-to-Book are not meaningful ratios in this state and are shown as N/A rather than a signed multiple.",
                    "metric": "Negative book equity",
                    "impact": "Reduced financial flexibility and no equity buffer against a downturn or credit tightening"
                })

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
            
            # Low or negative margins. Severity scales with magnitude: a
            # company losing multiples of its revenue (deeply negative margin)
            # is a materially different risk from one with merely thin
            # positive margins, and collapsing both into one Medium "Thin
            # Profit Margins" bucket understated the former. A large operating
            # loss gets its own High-severity flag and language.
            pm_str = str(fund.get("profit_margin", "N/A")).replace("%", "").replace(",", "")
            try:
                pm = float(pm_str)
                if pm < -25:
                    risks.append({
                        "title": "Substantial Operating Losses",
                        "category": "Profitability",
                        "severity": "High",
                        "description": f"Profit margin of {pm:.1f}% means the company is losing a large fraction of - potentially multiples of - its revenue. Losses of this scale burn cash and typically force external financing (often dilutive) or deep cost cuts to continue operating. This is a going-concern-adjacent signal, not merely thin profitability.",
                        "metric": f"{pm:.1f}%",
                        "impact": "Sustained losses at this scale pressure liquidity and raise the likelihood of a dilutive raise"
                    })
                elif pm < 5:
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
            fed_rate_value = indicators.get("fed_rate_value")
            fed_rate_label = indicators.get("fed_rate", "N/A")
            if fed_rate_value is not None:
                if fed_rate_value >= 5.0:
                    risks.append({
                        "title": "Interest Rate Vulnerability",
                        "category": "Macro",
                        "severity": "High",
                        "description": f"Federal funds rate at elevated levels ({fed_rate_label}). High rate environment pressures valuations through higher discount rates. Impacts borrowing costs and consumer spending. Extended high-rate regime could slow economic growth.",
                        "metric": fed_rate_label,
                        "impact": "Could result in 10-20% valuation compression if rates persist"
                    })
                elif fed_rate_value >= 4.0:
                    risks.append({
                        "title": "Persistent Higher Rates",
                        "category": "Macro",
                        "severity": "Medium",
                        "description": f"Rates remain elevated at {fed_rate_label}. This is constraining for growth stocks and companies with debt. Any attempts to raise rates further could be damaging.",
                        "metric": fed_rate_label,
                        "impact": "Additional rate hikes would negatively pressure valuations"
                    })

            # Inflation
            cpi_value = indicators.get("cpi_inflation_value")
            cpi_label = indicators.get("cpi_inflation", "N/A")
            if cpi_value is not None:
                if cpi_value >= 5.0:
                    risks.append({
                        "title": "Elevated Inflation",
                        "category": "Macro",
                        "severity": "High",
                        "description": f"Inflation at {cpi_label} is running well above the Fed's target. Creates significant headwinds for labor costs and input prices, and raises the likelihood of continued rate pressure. Companies with weak pricing power face material margin compression.",
                        "metric": cpi_label,
                        "impact": "Could pressure profit margins materially and keep rates higher for longer"
                    })
                elif cpi_value >= 3.0:
                    risks.append({
                        "title": "Inflation & Margin Pressure",
                        "category": "Macro",
                        "severity": "Medium",
                        "description": f"Inflation at {cpi_label} remains above target. Creates headwinds for labor costs and input prices. Companies with weak pricing power will face margin compression. May prompt additional rate hikes.",
                        "metric": cpi_label,
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
        
        return sorted_risks[:10]  # Return top 10 risks
    
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