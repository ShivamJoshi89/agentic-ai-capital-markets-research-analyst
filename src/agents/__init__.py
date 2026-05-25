"""
Agent module for Agentic AI Capital Markets Research Analyst
"""

from .market_data_agent import MarketDataAgent
from .fundamentals_agent import FinancialsAgent
from .sec_filing_agent import SECFilingAgent
from .news_agent import NewsAgent
from .macro_agent import MacroAgent
from .risk_agent import RiskAgent
from .report_agent import ReportAgent
from .critic_agent import CriticAgent

__all__ = [
    "MarketDataAgent",
    "FinancialsAgent",
    "SECFilingAgent",
    "NewsAgent",
    "MacroAgent",
    "RiskAgent",
    "ReportAgent",
    "CriticAgent",
]