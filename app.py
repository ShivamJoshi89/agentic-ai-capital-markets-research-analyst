"""
Agentic AI Capital Markets Research Analyst
Main Streamlit application - Phase 4
"""

import streamlit as st
import pandas as pd
import sys
import re
import html as html_lib
from pathlib import Path
from datetime import datetime
import logging

import pytz

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.market_data_agent import MarketDataAgent
from agents.fundamentals_agent import FinancialsAgent
from agents.news_agent import NewsAgent
from agents.macro_agent import MacroAgent
from agents.risk_agent import RiskAgent
from agents.report_agent import ReportAgent
from agents.peer_agent import PeerComparisonAgent
from data_sources.yfinance_client import YFinanceClient
from utils.helpers import validate_ticker, format_currency, format_percentage
from utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="AI Capital Markets Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# Institutional theme
# ============================================================
NAVY_BG = "#0a0e1a"
NAVY_SIDEBAR = "#0d1224"
CARD_BG = "#141929"
CARD_BORDER = "#1e2d4a"
GOLD = "#f0b429"
GREEN = "#00c851"
RED = "#ff4444"
BLUE = "#33b5e5"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#a0aec0"

st.markdown(f"""
    <style>
    /* ---------- Base surfaces ---------- */
    .stApp {{ background-color: {NAVY_BG}; }}
    [data-testid="stSidebar"] {{
        background-color: {NAVY_SIDEBAR};
        border-right: 1px solid {CARD_BORDER};
    }}
    h1, h2, h3 {{ color: {GOLD} !important; letter-spacing: 0.01em; }}
    hr {{ border-color: {CARD_BORDER}; }}

    /* ---------- st.metric as dark cards ---------- */
    [data-testid="stMetric"] {{
        background: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
    }}
    [data-testid="stMetricLabel"] {{
        color: {TEXT_SECONDARY} !important;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}
    [data-testid="stMetricValue"] {{ color: {TEXT_PRIMARY}; font-weight: 700; }}

    /* ---------- Sidebar navigation as buttons ---------- */
    [data-testid="stSidebar"] div[role="radiogroup"] > label {{
        display: block;
        padding: 0.55rem 0.9rem;
        margin: 2px 0;
        border-radius: 8px;
        border-left: 3px solid transparent;
        color: {TEXT_SECONDARY};
        cursor: pointer;
        transition: background 0.15s ease, color 0.15s ease;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {{
        background: {CARD_BG};
        color: {TEXT_PRIMARY};
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {{
        background: {CARD_BG};
        border-left: 3px solid {GOLD};
        color: {GOLD};
        font-weight: 600;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{
        display: none;  /* hide the radio circle */
    }}

    /* ---------- Inputs & buttons ---------- */
    [data-testid="stTextInput"] input {{
        background: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: 10px;
        color: {TEXT_PRIMARY};
        font-size: 1.05rem;
        padding: 0.7rem 1rem;
    }}
    [data-testid="stTextInput"] input:focus {{
        border: 1px solid {GOLD};
        box-shadow: 0 0 0 1px {GOLD};
    }}
    .stButton > button, .stDownloadButton > button {{
        background: {GOLD};
        color: {NAVY_BG};
        font-weight: 700;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        background: #d99e1b;
        color: {NAVY_BG};
    }}

    /* ---------- Custom metric cards ---------- */
    .aa-metric {{
        background: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: 10px;
        padding: 1rem 0.8rem;
        text-align: center;
        margin: 0.25rem 0;
    }}
    .aa-metric .value {{ font-size: 1.6rem; font-weight: 700; color: {TEXT_PRIMARY}; }}
    .aa-metric .value.pos {{ color: {GREEN}; }}
    .aa-metric .value.neg {{ color: {RED}; }}
    .aa-metric .label {{
        font-size: 0.72rem;
        color: {TEXT_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 0.35rem;
    }}

    /* ---------- Cards ---------- */
    .aa-card {{
        background: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.4rem 0;
    }}
    .aa-card .card-title {{ color: {GOLD}; font-weight: 700; font-size: 1rem; }}
    .aa-card .card-sub {{ color: {TEXT_SECONDARY}; font-size: 0.82rem; margin-top: 0.3rem; }}

    /* ---------- Hero ---------- */
    .aa-hero {{ text-align: center; padding: 2.2rem 1rem 1.4rem 1rem; }}
    .aa-hero .headline {{
        font-size: 2.6rem; font-weight: 800; color: {GOLD};
        letter-spacing: 0.01em; line-height: 1.15;
    }}
    .aa-hero .subline {{ font-size: 1.05rem; color: {TEXT_SECONDARY}; margin-top: 0.6rem; }}

    /* ---------- Agent pipeline ---------- */
    .aa-pipeline {{
        display: flex; align-items: stretch; justify-content: space-between;
        gap: 0; flex-wrap: wrap; margin: 0.5rem 0;
    }}
    .aa-step {{
        flex: 1; min-width: 96px; text-align: center;
        background: {CARD_BG}; border: 1px solid {CARD_BORDER};
        border-radius: 10px; padding: 0.75rem 0.3rem; margin: 2px;
    }}
    .aa-step .icon {{ font-size: 1.25rem; }}
    .aa-step .name {{
        color: {TEXT_SECONDARY}; font-size: 0.66rem; margin-top: 0.3rem;
        text-transform: uppercase; letter-spacing: 0.06em;
    }}
    .aa-connector {{
        display: flex; align-items: center; color: {GOLD};
        font-weight: 700; padding: 0 2px;
    }}

    /* ---------- Signal / risk / news cards (dark tints) ---------- */
    .aa-flag {{ padding: 1rem; border-radius: 10px; margin: 0.5rem 0; color: {TEXT_PRIMARY}; }}
    .aa-flag .flag-meta {{ color: {TEXT_SECONDARY}; font-size: 0.82rem; }}
    .aa-flag-opp {{ background: rgba(0, 200, 81, 0.08); border-left: 4px solid {GREEN}; }}
    .aa-flag-warn {{ background: rgba(240, 180, 41, 0.08); border-left: 4px solid {GOLD}; }}
    .aa-flag-risk {{ background: rgba(255, 68, 68, 0.08); border-left: 4px solid {RED}; }}
    .aa-news {{
        background: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-left: 4px solid {BLUE};
        padding: 1rem; border-radius: 10px; margin: 0.5rem 0;
    }}

    /* ---------- Research memo ---------- */
    .aa-memo {{
        background: {CARD_BG}; border: 1px solid {CARD_BORDER};
        border-radius: 12px; padding: 2rem 2.4rem; margin: 0.8rem 0;
    }}
    .aa-memo-header {{
        display: flex; justify-content: space-between; align-items: baseline;
        border-bottom: 2px solid {GOLD}; padding-bottom: 0.8rem; margin-bottom: 1.2rem;
    }}
    .aa-memo-header .memo-label {{
        color: {GOLD}; font-weight: 800; letter-spacing: 0.25em; font-size: 0.85rem;
    }}
    .aa-memo-header .memo-ticker {{ color: {TEXT_PRIMARY}; font-size: 1.5rem; font-weight: 800; }}
    .aa-memo-header .memo-date {{ color: {TEXT_SECONDARY}; font-size: 0.85rem; }}
    .aa-memo-section-title {{
        color: {GOLD}; font-weight: 700; font-size: 0.95rem;
        letter-spacing: 0.06em; margin: 1.1rem 0 0.4rem 0;
    }}
    .aa-memo-divider {{ border: none; border-top: 1px solid rgba(240, 180, 41, 0.4); margin: 0.9rem 0; }}
    .aa-memo-body {{ color: {TEXT_PRIMARY}; font-size: 0.92rem; line-height: 1.65; white-space: pre-wrap; }}
    .aa-case {{ padding: 1rem 1.2rem; border-radius: 10px; margin: 0.9rem 0; }}
    .aa-case .aa-memo-body {{ color: {TEXT_PRIMARY}; }}
    .aa-case-bull {{ background: rgba(0, 200, 81, 0.08); border: 1px solid {GREEN}; }}
    .aa-case-bear {{ background: rgba(255, 68, 68, 0.08); border: 1px solid {RED}; }}
    .aa-case-base {{ background: rgba(51, 181, 229, 0.08); border: 1px solid {BLUE}; }}
    .aa-case .case-tag {{ font-weight: 800; letter-spacing: 0.12em; font-size: 0.8rem; }}
    .aa-case-bull .case-tag {{ color: {GREEN}; }}
    .aa-case-bear .case-tag {{ color: {RED}; }}
    .aa-case-base .case-tag {{ color: {BLUE}; }}

    /* ---------- Sidebar brand & market status ---------- */
    .aa-brand {{ padding: 0.4rem 0 1rem 0; border-bottom: 1px solid {CARD_BORDER}; margin-bottom: 0.8rem; }}
    .aa-brand .brand-name {{ color: {GOLD}; font-size: 1.35rem; font-weight: 800; }}
    .aa-brand .brand-tag {{ color: {TEXT_SECONDARY}; font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase; }}
    .aa-market-status {{
        background: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 10px;
        padding: 0.7rem 0.9rem; margin-top: 1.2rem; font-size: 0.78rem; color: {TEXT_SECONDARY};
    }}
    .aa-market-status .dot {{ font-size: 0.7rem; }}
    .aa-market-status .status-open {{ color: {GREEN}; font-weight: 700; }}
    .aa-market-status .status-closed {{ color: {RED}; font-weight: 700; }}
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# UI helpers
# ============================================================

def metric_card(label: str, value, signed: bool = False, arrow: bool = False, suffix: str = ""):
    """Render a dark metric card. If signed, color the value green/red by sign
    and optionally prefix an up/down arrow."""

    css_class = ""
    arrow_char = ""
    display = "N/A" if value is None else str(value)

    if signed and value is not None:
        try:
            numeric = float(str(value).replace("%", "").replace(",", ""))
            if numeric > 0:
                css_class = "pos"
                arrow_char = "▲ " if arrow else ""
                if not str(value).startswith("+"):
                    display = f"+{value}"
            elif numeric < 0:
                css_class = "neg"
                arrow_char = "▼ " if arrow else ""
        except (ValueError, TypeError):
            pass

    st.markdown(f"""
    <div class="aa-metric">
        <div class="value {css_class}">{arrow_char}{html_lib.escape(display)}{suffix}</div>
        <div class="label">{html_lib.escape(label)}</div>
    </div>
    """, unsafe_allow_html=True)


def render_market_status():
    """Sidebar market status indicator with current date/time (US/Eastern)"""
    now_et = datetime.now(pytz.timezone("US/Eastern"))
    is_weekday = now_et.weekday() < 5
    after_open = (now_et.hour, now_et.minute) >= (9, 30)
    before_close = (now_et.hour, now_et.minute) < (16, 0)
    is_open = is_weekday and after_open and before_close

    if is_open:
        status = '<span class="dot">🟢</span> <span class="status-open">NYSE OPEN</span>'
    else:
        status = '<span class="dot">🔴</span> <span class="status-closed">NYSE CLOSED</span>'

    st.markdown(f"""
    <div class="aa-market-status">
        {status}<br>
        {now_et.strftime('%A, %b %d %Y')}<br>
        {now_et.strftime('%I:%M %p')} ET
    </div>
    """, unsafe_allow_html=True)


def split_memo_sections(memo: str):
    """Split LLM memo text into (title, body) sections.

    Header lines are numbered and/or mostly-uppercase (e.g. '7. BULL CASE').
    Returns [(None, memo)] if no headers are found.
    """
    header_re = re.compile(r"^\s*(?:\d+\.\s*)?([A-Z][A-Z0-9 /&()',\.\-]{3,}):?\s*$")

    sections = []
    current_title = None
    current_lines = []

    for line in memo.splitlines():
        match = header_re.match(line.strip())
        if match:
            if current_title is not None or current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = match.group(1).strip().rstrip(":")
            current_lines = []
        else:
            current_lines.append(line)

    if current_title is not None or current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    if not any(title for title, _ in sections):
        return [(None, memo.strip())]

    return sections


# Initialize session state
if "ticker" not in st.session_state:
    st.session_state.ticker = ""
if "market_data" not in st.session_state:
    st.session_state.market_data = None
if "fundamentals_data" not in st.session_state:
    st.session_state.fundamentals_data = None
if "company_info" not in st.session_state:
    st.session_state.company_info = None
if "news_data" not in st.session_state:
    st.session_state.news_data = None
if "macro_data" not in st.session_state:
    st.session_state.macro_data = None
if "risk_data" not in st.session_state:
    st.session_state.risk_data = None
if "memo_data" not in st.session_state:
    st.session_state.memo_data = None
if "peer_data" not in st.session_state:
    st.session_state.peer_data = None


def format_large_number(value):
    """Format large numbers with B, M, K suffix"""
    if value is None:
        return "N/A"
    try:
        if value >= 1_000_000_000:
            return f"${value/1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"${value/1_000_000:.2f}M"
        elif value >= 1_000:
            return f"${value/1_000:.2f}K"
        else:
            return f"${value:.2f}"
    except:
        return "N/A"


def fetch_analysis(ticker: str):
    """Fetch complete analysis including risks and memo"""
    
    ticker = ticker.upper().strip()
    
    # Validate ticker
    if not validate_ticker(ticker):
        st.error(f"❌ Invalid ticker format: '{ticker}'. Please enter 1-5 uppercase letters (e.g., JPM, AAPL)")
        return False
    
    progress = st.progress(0, text=f"🔎 Initializing analysis pipeline for {ticker}...")

    try:
        # Fetch company info
        progress.progress(8, text=f"🏢 Resolving company profile for {ticker}...")
        yfinance_client = YFinanceClient()
        company_info = yfinance_client.get_company_info(ticker)

        if not company_info or not company_info.get("success"):
            progress.empty()
            st.error(f"❌ Could not find ticker '{ticker}'. Please check the symbol and try again.")
            logger.error(f"Failed to fetch company info for {ticker}")
            return False

        # Fetch market data
        progress.progress(20, text="📈 Market Data Agent — prices, returns, volatility...")
        market_agent = MarketDataAgent()
        market_data = market_agent.run(ticker)

        if not market_data.get("success"):
            progress.empty()
            st.error(f"❌ Failed to fetch market data for {ticker}")
            logger.error(f"Market data fetch failed: {market_data.get('error')}")
            return False

        # Fetch fundamentals
        progress.progress(34, text="💰 Fundamentals Agent — financials and ratios...")
        fundamentals_agent = FinancialsAgent()
        fundamentals_data = fundamentals_agent.run(ticker)

        if not fundamentals_data.get("success"):
            st.warning(f"⚠️ Some fundamentals data unavailable for {ticker}")

        # Fetch news
        progress.progress(48, text="📰 News Agent — headlines and sentiment...")
        news_agent = NewsAgent()
        company_name = company_info.get("company_name", ticker)
        news_data = news_agent.run(ticker, company_name)

        if not news_data.get("success"):
            st.warning(f"⚠️ Could not fetch news for {ticker}")
            news_data = {"success": False, "articles": []}

        # Fetch macro data
        progress.progress(60, text="🌍 Macro Agent — FRED economic indicators...")
        macro_agent = MacroAgent()
        sector = company_info.get("sector", None)
        macro_data = macro_agent.run(ticker=ticker, sector=sector)

        if not macro_data.get("success"):
            st.warning(f"⚠️ Could not fetch macro data")
            macro_data = {"success": False}

        # Build peer comparison
        progress.progress(72, text="🏦 Peer Agent — comparable companies analysis...")
        peer_agent = PeerComparisonAgent()
        peer_data = peer_agent.run(ticker)

        if not peer_data.get("success"):
            st.warning(f"⚠️ Could not build peer comparison for {ticker}")
            peer_data = {"success": False}

        # Analyze risks
        progress.progress(84, text="⚠️ Risk Agent — risk factors and special situations...")
        risk_agent = RiskAgent()
        all_analysis_data = {
            "market_data": market_data,
            "fundamentals_data": fundamentals_data,
            "news_data": news_data,
            "company_info": company_info,
            "macro_data": macro_data
        }
        risk_data = risk_agent.run(ticker, all_analysis_data)

        if not risk_data.get("success"):
            st.warning(f"⚠️ Could not complete risk analysis")
            risk_data = {"success": False, "risks": []}

        # Generate final memo
        progress.progress(94, text="📝 Report Agent — drafting research memo...")
        report_agent = ReportAgent()
        all_analysis_data["risk_data"] = risk_data
        memo_data = report_agent.run(ticker, all_analysis_data)

        if not memo_data.get("success"):
            st.warning(f"⚠️ Could not generate full memo with LLM, using fallback")
            # Fallback memo data still works even if LLM fails

        progress.progress(100, text="✅ Analysis complete")

        # Store in session state
        st.session_state.ticker = ticker
        st.session_state.market_data = market_data
        st.session_state.fundamentals_data = fundamentals_data
        st.session_state.company_info = company_info
        st.session_state.news_data = news_data
        st.session_state.macro_data = macro_data
        st.session_state.risk_data = risk_data
        st.session_state.memo_data = memo_data
        st.session_state.peer_data = peer_data

        progress.empty()
        return True

    except Exception as e:
        progress.empty()
        st.error(f"❌ Error fetching data: {str(e)}")
        logger.error(f"Error in fetch_analysis: {str(e)}")
        return False


def show_home_page():
    """Display home page"""

    # Hero section
    st.markdown("""
    <div class="aa-hero">
        <div class="headline">Institutional-Grade Equity Research</div>
        <div class="subline">Powered by Multi-Agent AI</div>
    </div>
    """, unsafe_allow_html=True)

    # Centered search bar
    _, center, _ = st.columns([1, 2, 1])
    with center:
        ticker_input = st.text_input(
            "Enter Stock Ticker",
            placeholder="Enter a ticker — JPM, AAPL, NVDA, MS...",
            key="ticker_input",
            label_visibility="collapsed"
        )
        generate_button = st.button(
            "🔍 Generate Full Analysis",
            key="generate_button",
            use_container_width=True
        )

    if generate_button:
        if not ticker_input:
            st.warning("⚠️ Please enter a stock ticker")
        else:
            success = fetch_analysis(ticker_input)
            if success:
                st.success(f"✅ Complete analysis generated for {ticker_input.upper()}!")
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Feature cards
    feature_cards = [
        ("🤖", "8 AI Agents", "Specialized analysts working in concert"),
        ("🔌", "6 Data Sources", "yfinance, FRED, Google News, SEC EDGAR, NewsAPI, OpenAI"),
        ("⚡", "Real-Time Data", "Live market, macro and headline feeds"),
        ("🏛️", "Wall Street Methodology", "Comps, earnings quality, bull/base/bear cases"),
    ]
    cols = st.columns(4)
    for col, (icon, title, sub) in zip(cols, feature_cards):
        with col:
            st.markdown(f"""
            <div class="aa-card" style="text-align:center; min-height: 138px;">
                <div style="font-size:1.6rem;">{icon}</div>
                <div class="card-title">{title}</div>
                <div class="card-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    # Agent pipeline visualization
    st.markdown("---")
    st.subheader("Analysis Pipeline")

    pipeline_steps = [
        ("📈", "Market Data"),
        ("💰", "Fundamentals"),
        ("📰", "News"),
        ("🌍", "Macro"),
        ("🏦", "Peers"),
        ("⚠️", "Risk"),
        ("📝", "Report"),
    ]
    step_html = '<div class="aa-connector">→</div>'.join(
        f'<div class="aa-step"><div class="icon">{icon}</div><div class="name">{name}</div></div>'
        for icon, name in pipeline_steps
    )
    st.markdown(f'<div class="aa-pipeline">{step_html}</div>', unsafe_allow_html=True)

    # Show last analyzed ticker if available
    if st.session_state.ticker:
        st.markdown("---")
        st.subheader(f"📍 Last Analyzed: {st.session_state.ticker}")

        col1, col2, col3 = st.columns(3)

        if st.session_state.market_data and st.session_state.market_data.get("success"):
            metrics = st.session_state.market_data.get("metrics", {})
            with col1:
                st.metric(
                    "Current Price",
                    f"${metrics.get('latest_price', 'N/A')}",
                    delta=f"{metrics.get('price_change_pct', 0):.2f}%"
                )

        if st.session_state.company_info and st.session_state.company_info.get("success"):
            with col2:
                st.metric("Market Cap", format_large_number(st.session_state.company_info.get("market_cap")))

            with col3:
                st.metric("Sector", st.session_state.company_info.get("sector", "N/A"))


def show_company_overview():
    """Display company overview page"""
    
    if not st.session_state.company_info or not st.session_state.company_info.get("success"):
        st.warning("⚠️ No company data available. Please analyze a ticker first.")
        return
    
    info = st.session_state.company_info
    
    st.title(f"🏢 {info.get('company_name', 'N/A')} ({info.get('ticker', 'N/A')})")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Current Price", f"${info.get('current_price', 'N/A')}")
    with col2:
        st.metric("Market Cap", format_large_number(info.get("market_cap")))
    with col3:
        st.metric("Exchange", info.get("exchange", "N/A"))
    with col4:
        st.metric("Currency", info.get("currency", "USD"))
    
    # Company details
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Company Information")
        st.write(f"**Sector:** {info.get('sector', 'N/A')}")
        st.write(f"**Industry:** {info.get('industry', 'N/A')}")
        st.write(f"**Country:** {info.get('country', 'N/A')}")
        st.write(f"**Employees:** {info.get('employees', 'N/A'):,}" if info.get('employees') else "**Employees:** N/A")
        st.write(f"**Website:** {info.get('website', 'N/A')}")
    
    with col2:
        st.subheader("📈 Price Range (52 weeks)")
        st.write(f"**High:** ${info.get('52_week_high', 'N/A')}")
        st.write(f"**Low:** ${info.get('52_week_low', 'N/A')}")
        st.write(f"**Day High:** ${info.get('day_high', 'N/A')}")
        st.write(f"**Day Low:** ${info.get('day_low', 'N/A')}")
        st.write(f"**Previous Close:** ${info.get('previous_close', 'N/A')}")
    
    # Business summary
    if info.get('business_summary'):
        st.subheader("📖 Business Summary")
        st.write(info.get('business_summary'))


def show_market_performance():
    """Display market performance page"""
    
    if not st.session_state.market_data or not st.session_state.market_data.get("success"):
        st.warning("⚠️ No market data available. Please analyze a ticker first.")
        return
    
    ticker = st.session_state.ticker
    market_data = st.session_state.market_data
    metrics = market_data.get("metrics", {})
    
    st.title(f"📈 Market Performance - {ticker}")

    # Price and returns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Current Price",
            f"${metrics.get('latest_price', 'N/A')}",
            delta=f"{metrics.get('price_change_pct', 0):.2f}%"
        )

    with col2:
        metric_card("1-Month Return", metrics.get("one_month_return"), signed=True, arrow=True, suffix="%")

    with col3:
        metric_card("3-Month Return", metrics.get("three_month_return"), signed=True, arrow=True, suffix="%")

    with col4:
        metric_card("6-Month Return", metrics.get("six_month_return"), signed=True, arrow=True, suffix="%")

    # Technical metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card("YTD Return", metrics.get("ytd_return"), signed=True, arrow=True, suffix="%")

    with col2:
        metric_card("Volatility (Annual)", metrics.get("volatility"), suffix="%")

    with col3:
        metric_card("Max Drawdown", metrics.get("max_drawdown"), signed=True, arrow=True, suffix="%")

    with col4:
        avg_volume = metrics.get("avg_volume")
        metric_card("Avg Volume", f"{avg_volume:,.0f}" if avg_volume else None)

    # Moving averages
    st.subheader("📊 Moving Averages")
    col1, col2, col3 = st.columns(3)

    with col1:
        metric_card("20-Day MA", f"${metrics.get('ma_20', 'N/A')}")

    with col2:
        metric_card("50-Day MA", f"${metrics.get('ma_50', 'N/A')}")

    with col3:
        metric_card("200-Day MA", f"${metrics.get('ma_200', 'N/A')}")

    # Price chart: stacked panels (price above, volume below) on a shared
    # x-axis - one scale per panel, no dual-axis overlay
    if market_data.get("data") is not None:
        st.subheader("📉 Price Chart (1 Year)")

        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        data = market_data.get("data")

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.72, 0.28]
        )

        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["Close"],
            mode="lines",
            name="Close",
            line=dict(color=GOLD, width=2),
            hovertemplate="$%{y:.2f}<extra>Close</extra>"
        ), row=1, col=1)

        # Volume bars colored by up/down day
        up_day = data["Close"].diff().fillna(0) >= 0
        volume_colors = [GREEN if up else RED for up in up_day]

        fig.add_trace(go.Bar(
            x=data.index,
            y=data["Volume"],
            name="Volume",
            marker_color=volume_colors,
            marker_line_width=0,
            opacity=0.8,
            hovertemplate="%{y:,.0f}<extra>Volume</extra>"
        ), row=2, col=1)

        fig.update_layout(
            title=dict(text=f"{ticker} — 1 Year Price History", font=dict(color=GOLD, size=16)),
            paper_bgcolor=NAVY_BG,
            plot_bgcolor=CARD_BG,
            font=dict(color=TEXT_SECONDARY),
            hovermode="x unified",
            showlegend=False,
            height=540,
            margin=dict(l=10, r=10, t=50, b=10),
            bargap=0.1
        )
        fig.update_xaxes(gridcolor=CARD_BORDER, zeroline=False, showline=False)
        fig.update_yaxes(gridcolor=CARD_BORDER, zeroline=False, showline=False)
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)


def show_fundamentals():
    """Display fundamentals page"""
    
    if not st.session_state.fundamentals_data or not st.session_state.fundamentals_data.get("success"):
        st.warning("⚠️ No fundamentals data available for this ticker.")
        return
    
    ticker = st.session_state.ticker
    fundamentals = st.session_state.fundamentals_data.get("fundamentals", {})
    
    st.title(f"💰 Financial Fundamentals - {ticker}")
    
    # Income Statement
    st.subheader("📊 Income Statement")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Revenue", fundamentals.get("revenue", "N/A"))
    with col2:
        st.metric("Net Income", fundamentals.get("net_income", "N/A"))
    with col3:
        st.metric("Free Cash Flow", fundamentals.get("free_cash_flow", "N/A"))
    with col4:
        st.metric("Operating CF", fundamentals.get("operating_cash_flow", "N/A"))
    
    # Balance Sheet
    st.subheader("🏦 Balance Sheet")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Assets", fundamentals.get("total_assets", "N/A"))
    with col2:
        st.metric("Total Liabilities", fundamentals.get("total_liabilities", "N/A"))
    with col3:
        st.metric("Total Equity", fundamentals.get("total_equity", "N/A"))
    with col4:
        st.metric("Total Debt", fundamentals.get("total_debt", "N/A"))
    
    # Profitability
    st.subheader("📈 Profitability Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Gross Margin", fundamentals.get("gross_margin", "N/A"))
    with col2:
        st.metric("Operating Margin", fundamentals.get("operating_margin", "N/A"))
    with col3:
        st.metric("Profit Margin", fundamentals.get("profit_margin", "N/A"))
    with col4:
        st.metric("ROE", fundamentals.get("roe", "N/A"))
    
    # Valuation
    st.subheader("💎 Valuation Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("EPS", fundamentals.get("eps", "N/A"))
    with col2:
        st.metric("P/E Ratio", fundamentals.get("pe_ratio", "N/A"))
    with col3:
        st.metric("P/B Ratio", fundamentals.get("pb_ratio", "N/A"))
    with col4:
        st.metric("Dividend Yield", fundamentals.get("dividend_yield", "N/A"))
    
    # Leverage
    st.subheader("⚖️ Leverage & Liquidity")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Debt-to-Equity", fundamentals.get("debt_to_equity", "N/A"))
    with col2:
        st.metric("Current Ratio", fundamentals.get("current_ratio", "N/A"))
    with col3:
        st.metric("Quick Ratio", fundamentals.get("quick_ratio", "N/A"))

    if fundamentals.get("is_financial_sector"):
        st.info(
            "ℹ️ **Financial institution note:** balance-sheet totals and D/E are drawn from "
            "reported statements (D/E = total debt ÷ stockholders' equity). Current and quick "
            "ratios are not reported by banks — their balance sheets have no current/non-current "
            "split — and gross margin is not a reported bank metric. Bank leverage is formally "
            "assessed via regulatory capital (e.g., Tier 1 ratio) rather than simple D/E. "
            "Operating/free cash flow for banks is dominated by lending and deposit flows and is "
            "routinely large and negative — it is not comparable to industrial-company FCF."
        )


def show_peer_comparison():
    """Display peer comparison page"""

    if not st.session_state.peer_data or not st.session_state.peer_data.get("success"):
        st.warning("⚠️ No peer comparison available. Please analyze a ticker first.")
        return

    ticker = st.session_state.ticker
    peer_data = st.session_state.peer_data
    companies = peer_data.get("companies", [])

    st.title(f"🏦 Peer Comparison - {ticker}")
    st.caption(
        f"Sector: {peer_data.get('sector', 'N/A')} | Industry: {peer_data.get('industry', 'N/A')} | "
        f"{len(companies) - 1} peers identified via yfinance"
    )

    # Metric key -> (column label, higher_is_better, format string)
    metric_config = {
        "pe_ratio": ("P/E Ratio", False, "{:.2f}"),
        "revenue_growth": ("Revenue Growth", True, "{:.1f}%"),
        "profit_margin": ("Profit Margin", True, "{:.1f}%"),
        "roe": ("ROE", True, "{:.1f}%"),
        "debt_to_equity": ("Debt-to-Equity", False, "{:.1f}"),
    }

    # Build comparison table (target first, marked with a star)
    rows = []
    for company in companies:
        is_target = company.get("ticker") == ticker
        row = {
            "Ticker": f"⭐ {company.get('ticker')}" if is_target else company.get("ticker"),
            "Company": company.get("company", "N/A"),
        }
        for key, (label, _, _) in metric_config.items():
            row[label] = company.get(key)
        rows.append(row)

    df = pd.DataFrame(rows).set_index("Ticker")

    def highlight_best_worst(column, higher_is_better):
        """Green for best value in column, red for worst"""
        numeric = pd.to_numeric(column, errors="coerce")
        styles = [""] * len(column)
        if numeric.notna().sum() >= 2:
            best_idx = numeric.idxmax() if higher_is_better else numeric.idxmin()
            worst_idx = numeric.idxmin() if higher_is_better else numeric.idxmax()
            for i, idx in enumerate(column.index):
                if idx == best_idx:
                    styles[i] = f"background-color: rgba(0, 200, 81, 0.18); color: {GREEN}; font-weight: bold"
                elif idx == worst_idx:
                    styles[i] = f"background-color: rgba(255, 68, 68, 0.18); color: {RED}; font-weight: bold"
        return styles

    styler = df.style
    for key, (label, higher_is_better, fmt) in metric_config.items():
        styler = styler.apply(
            lambda col, hib=higher_is_better: highlight_best_worst(col, hib),
            subset=[label]
        )
        styler = styler.format({label: fmt}, na_rep="N/A")

    st.dataframe(styler, use_container_width=True)
    st.caption("🟩 Best in class | 🟥 Worst in class (lower is better for P/E and Debt-to-Equity)")

    st.markdown("---")

    # Rank summary for the analyzed company
    st.subheader(f"📊 How {ticker} Ranks Against Peers")

    rank_cols = st.columns(len(metric_config))
    for i, (key, (label, higher_is_better, _)) in enumerate(metric_config.items()):
        values = pd.Series(
            {c.get("ticker"): c.get(key) for c in companies}, dtype="float64"
        ).dropna()

        with rank_cols[i]:
            if ticker in values.index and len(values) >= 2:
                rank = int(values.rank(ascending=not higher_is_better, method="min")[ticker])
                st.metric(label, f"#{rank} of {len(values)}")
            else:
                st.metric(label, "N/A")

    if peer_data.get("sector") == "Financial Services":
        st.info(
            "ℹ️ Debt-to-Equity is often unavailable for banks — financial institutions "
            "are assessed on regulatory capital metrics instead."
        )


def show_news_sentiment():
    """Display news and sentiment page"""
    
    if not st.session_state.news_data or not st.session_state.news_data.get("success"):
        st.info("📰 News data not available for this ticker. Sentiment analysis coming soon.")
        return
    
    ticker = st.session_state.ticker
    news_data = st.session_state.news_data
    
    st.title(f"📰 News & Sentiment - {ticker}")
    
    # Overall sentiment
    overall_sentiment = news_data.get("overall_sentiment", "Neutral")
    sentiment_counts = news_data.get("sentiment_counts", {})
    total_articles = news_data.get("total_articles", 0)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        sentiment_color = "green" if overall_sentiment == "Positive" else "orange" if overall_sentiment == "Neutral" else "red"
        st.metric("Overall Sentiment", overall_sentiment)
    
    with col2:
        st.metric("Positive Articles", sentiment_counts.get("positive", 0))
    
    with col3:
        st.metric("Neutral Articles", sentiment_counts.get("neutral", 0))
    
    with col4:
        st.metric("Negative Articles", sentiment_counts.get("negative", 0))

    st.markdown("---")

    # Special situations radar (flags produced by the Risk Agent)
    st.subheader("🎯 Special Situations Radar")

    risk_data = st.session_state.risk_data or {}
    special_flags = risk_data.get("special_situations", [])

    if not special_flags:
        st.caption("No special situation signals detected in recent headlines.")
    else:
        opportunity_count = sum(1 for f in special_flags if f.get("signal_type") == "opportunity_signal")
        risk_count = len(special_flags) - opportunity_count
        st.write(f"**{len(special_flags)} signal(s) detected** — ⚡ {opportunity_count} opportunity | ⚠️ {risk_count} risk")

        for flag in special_flags:
            is_opportunity = flag.get("signal_type") == "opportunity_signal"
            icon = "⚡" if is_opportunity else "⚠️"
            signal_label = "Opportunity Signal" if is_opportunity else "Risk Signal"
            flag_class = "aa-flag-opp" if is_opportunity else "aa-flag-warn"

            st.markdown(f"""
            <div class="aa-flag {flag_class}">
                <strong>{icon} {flag.get('category', 'Unknown')}</strong>
                <span class="flag-meta">— {signal_label} <em>(matched: "{flag.get('matched_keyword', '')}")</em></span><br>
                {flag.get('headline', '')}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Articles
    st.subheader(f"📋 Recent Headlines ({total_articles} articles)")
    
    articles = news_data.get("articles", [])
    
    if not articles:
        st.info("No recent articles found for this ticker.")
    else:
        for idx, article in enumerate(articles, 1):
            sentiment = article.get("sentiment", "Neutral")

            if sentiment == "Positive":
                badge = f'<span style="color:{GREEN}; font-weight:700;">▲ Positive</span>'
            elif sentiment == "Negative":
                badge = f'<span style="color:{RED}; font-weight:700;">▼ Negative</span>'
            else:
                badge = f'<span style="color:{TEXT_SECONDARY}; font-weight:700;">● Neutral</span>'

            title = html_lib.escape(article.get("title", "N/A"))
            description = html_lib.escape(article.get("description", "")[:200])
            url = article.get("url", "#")

            st.markdown(f"""
            <div class="aa-news">
                <strong>{title}</strong><br>
                <span class="flag-meta" style="color:{TEXT_SECONDARY}; font-size:0.8rem;">
                    {badge} &nbsp;|&nbsp; 📅 {html_lib.escape(str(article.get('published_date', 'N/A')))}
                    &nbsp;|&nbsp; 📰 {html_lib.escape(str(article.get('source', 'N/A')))}
                </span>
                <p style="color:{TEXT_SECONDARY}; font-size:0.88rem; margin:0.5rem 0 0.3rem 0;">{description}...</p>
                <a href="{url}" style="color:{GOLD};">Read More →</a>
            </div>
            """, unsafe_allow_html=True)


def show_macro_environment():
    """Display macroeconomic environment page"""
    
    if not st.session_state.macro_data or not st.session_state.macro_data.get("success"):
        st.info("🌍 Macroeconomic data temporarily unavailable. Check back soon.")
        return
    
    ticker = st.session_state.ticker
    macro_data = st.session_state.macro_data
    indicators = macro_data.get("indicators", {})
    analysis = macro_data.get("analysis", {})
    
    st.title(f"🌍 Macroeconomic Environment - {ticker}")
    
    # Current indicators
    st.subheader("📊 Key Economic Indicators")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Federal Funds Rate", indicators.get("fed_rate", "N/A"))
    
    with col2:
        st.metric("10-Year Treasury Yield", indicators.get("10y_treasury", "N/A"))
    
    with col3:
        st.metric("Inflation (CPI)", indicators.get("cpi_inflation", "N/A"))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Unemployment Rate", indicators.get("unemployment_rate", "N/A"))
    
    with col2:
        st.metric("VIX Index", indicators.get("vix_index", "N/A"))
    
    st.markdown("---")
    
    # Analysis
    st.subheader("💡 Macro Analysis & Impact")
    
    if analysis:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Interest Rate Environment**")
            st.info(analysis.get("interest_rates", "N/A"))
            
            st.write("**Treasury Yields**")
            st.info(analysis.get("treasury_impact", "N/A"))
        
        with col2:
            st.write("**Inflation Outlook**")
            st.info(analysis.get("inflation_impact", "N/A"))
            
            st.write("**Labor Market**")
            st.info(analysis.get("labor_market", "N/A"))
        
        st.markdown("---")
        
        st.write("**Overall Macro Summary**")
        st.success(analysis.get("summary", "N/A"))


def show_risk_analysis():
    """Display risk analysis page - IMPROVED VERSION"""
    
    if not st.session_state.risk_data or not st.session_state.risk_data.get("success"):
        st.info("⚠️ Risk analysis not available. Please analyze a ticker first.")
        return
    
    ticker = st.session_state.ticker
    risk_data = st.session_state.risk_data
    risks = risk_data.get("risks", [])
    
    st.title(f"⚠️ Risk Analysis - {ticker}")
    
    # Risk summary metrics
    st.subheader("Risk Profile Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    high_risks = sum(1 for r in risks if r.get("severity") == "High")
    medium_risks = sum(1 for r in risks if r.get("severity") == "Medium")
    low_risks = sum(1 for r in risks if r.get("severity") == "Low")
    total_risks = len(risks)
    
    with col1:
        st.metric("🔴 High Severity", high_risks, help="Risks requiring immediate attention")
    with col2:
        st.metric("🟡 Medium Severity", medium_risks, help="Risks to monitor")
    with col3:
        st.metric("🟢 Low Severity", low_risks, help="Minor risks")
    with col4:
        # Risk score
        risk_score = (high_risks * 100 + medium_risks * 50) / max(total_risks, 1)
        st.metric("Risk Score", f"{min(risk_score, 100):.0f}/100")
    
    st.markdown("---")
    
    # Risk Assessment Summary
    st.subheader("Overall Assessment")
    summary_text = risk_data.get("summary", "Risk analysis completed.")
    
    # Color code the summary box based on risk level
    if high_risks >= 2:
        st.error(summary_text)
    elif high_risks == 1:
        st.warning(summary_text)
    else:
        st.success(summary_text)
    
    st.markdown("---")
    
    # Detailed risk breakdown
    st.subheader("Detailed Risk Analysis")
    
    if not risks:
        st.info("No significant risks identified.")
    else:
        # Risk categories
        categories = {}
        for risk in risks:
            cat = risk.get("category", "Other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(risk)
        
        # Display risks organized by category
        for category in ["Valuation", "Leverage", "Profitability", "Market", "Macro", "Sentiment", "Sector"]:
            if category in categories:
                st.write(f"### {category} Risks")
                
                for risk in categories[category]:
                    severity = risk.get("severity", "Low")

                    # Dark-tinted card by severity
                    if severity == "High":
                        icon = "🔴"
                        flag_class = "aa-flag-risk"
                        severity_color = RED
                    elif severity == "Medium":
                        icon = "🟡"
                        flag_class = "aa-flag-warn"
                        severity_color = GOLD
                    else:
                        icon = "🟢"
                        flag_class = "aa-flag-opp"
                        severity_color = GREEN

                    st.markdown(f"""
                    <div class="aa-flag {flag_class}" style="padding: 1.3rem;">
                        <div style="font-size:1.05rem; font-weight:700; margin-bottom:0.5rem;">
                            {icon} {risk.get('title', 'Unknown Risk')}
                            <span style="color:{severity_color}; font-size:0.78rem; letter-spacing:0.08em;
                                         margin-left:0.6rem;">{severity.upper()} SEVERITY</span>
                        </div>
                        <p style="margin:0.3rem 0;">{risk.get('description', 'No description')}</p>
                        <p class="flag-meta" style="margin:0.3rem 0;">
                            <strong>Metric:</strong> {risk.get('metric', 'N/A')}
                            &nbsp;|&nbsp; <strong>Potential Impact:</strong> {risk.get('impact', 'Unknown')}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Risk mitigation recommendations
    st.subheader("Risk Mitigation Considerations")
    
    if high_risks >= 2:
        st.warning("""
        **High Risk Environment:** Consider:
        - Reducing position size relative to portfolio
        - Setting tighter stop-loss levels
        - Diversifying away from this risk profile
        - Waiting for risk factors to resolve
        """)
    elif high_risks == 1:
        st.info("""
        **Elevated Risk:** Recommend:
        - Monitoring key risk drivers closely
        - Appropriate position sizing
        - Clear exit criteria if thesis breaks down
        """)
    else:
        st.success("""
        **Acceptable Risk Profile:** Standard approach:
        - Regular monitoring of fundamentals
        - Quarterly review of risk factors
        - Rebalance as needed
        """)

def show_research_memo():
    """Display final research memo page"""
    
    if not st.session_state.ticker:
        st.info("📋 Full research memo coming soon. Enter a ticker on the Home page to generate.")
        return
    
    ticker = st.session_state.ticker
    memo_data = st.session_state.memo_data
    
    st.title(f"📋 Investment Research Memo - {ticker}")
    
    if not memo_data or not memo_data.get("success"):
        st.warning("⚠️ Memo generation encountered an issue, but analysis is complete.")
        memo = memo_data.get("memo", "") if memo_data else ""
    else:
        memo = memo_data.get("memo", "")

    if memo:
        # Styled analyst-report container
        report_date = datetime.now(pytz.timezone("US/Eastern")).strftime("%B %d, %Y")

        section_parts = []
        for title, body in split_memo_sections(memo):
            safe_body = html_lib.escape(body)
            title_upper = (title or "").upper()

            if "BULL" in title_upper:
                section_parts.append(
                    f'<div class="aa-case aa-case-bull"><div class="case-tag">🐂 {html_lib.escape(title)}</div>'
                    f'<div class="aa-memo-body">{safe_body}</div></div>'
                )
            elif "BEAR" in title_upper:
                section_parts.append(
                    f'<div class="aa-case aa-case-bear"><div class="case-tag">🐻 {html_lib.escape(title)}</div>'
                    f'<div class="aa-memo-body">{safe_body}</div></div>'
                )
            elif "BASE" in title_upper:
                section_parts.append(
                    f'<div class="aa-case aa-case-base"><div class="case-tag">⚖️ {html_lib.escape(title)}</div>'
                    f'<div class="aa-memo-body">{safe_body}</div></div>'
                )
            elif title:
                section_parts.append(
                    f'<hr class="aa-memo-divider">'
                    f'<div class="aa-memo-section-title">{html_lib.escape(title)}</div>'
                    f'<div class="aa-memo-body">{safe_body}</div>'
                )
            elif body:
                section_parts.append(f'<div class="aa-memo-body">{safe_body}</div>')

        st.markdown(f"""
        <div class="aa-memo">
            <div class="aa-memo-header">
                <div>
                    <div class="memo-label">RESEARCH MEMO</div>
                    <div class="memo-ticker">{html_lib.escape(ticker)}</div>
                </div>
                <div class="memo-date">{report_date}<br>Multi-Agent AI Research Desk</div>
            </div>
            {''.join(section_parts)}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        
        st.markdown("""
        ### 📌 Important Disclaimers
        
        ✓ This analysis is **for educational purposes only**
        ✓ Not investment advice or recommendations
        ✓ Not a substitute for professional financial advice
        ✓ Always consult with qualified financial advisors
        ✓ Past performance does not guarantee future results
        ✓ All investments carry risk, including potential loss of principal
        
        **Data Sources:** yfinance, SEC EDGAR, Google News RSS, FRED API
        
        **Analysis Method:** Multi-agent AI system with fundamental and technical analysis
        """)
        
        # Download memo option
        col1, col2 = st.columns([1, 1])
        with col1:
            memo_text = f"INVESTMENT RESEARCH MEMO\n{ticker}\n\n{memo}"
            st.download_button(
                label="📥 Download Memo (Text)",
                data=memo_text,
                file_name=f"{ticker}_research_memo.txt",
                mime="text/plain"
            )
    else:
        st.info("📋 Generating memo... Please wait or refresh the page.")


def show_about():
    """Display about page"""
    
    st.title("ℹ️ About This Project")
    
    st.markdown("""
        ## Agentic AI Capital Markets Research Analyst
        
        ### Project Vision
        
        This project demonstrates how AI agents can automate financial research workflows
        to support investment decision-making.
        
        ### Current Capabilities (Phase 4 Complete)
        
        ✅ **Market Data Analysis**
        - Historical stock prices from yfinance
        - Returns (1M, 3M, 6M, YTD)
        - Volatility and moving averages
        - Maximum drawdown
        - Volume analysis
        - Interactive price charts
        
        ✅ **Financial Fundamentals**
        - Income statement data (Revenue, Net Income, Cash Flow)
        - Balance sheet metrics (Assets, Liabilities, Equity, Debt)
        - Profitability ratios (Margins, ROE, ROA)
        - Valuation metrics (P/E, P/B, EPS, Dividend Yield)
        - Leverage ratios (Debt-to-Equity, Current Ratio)
        
        ✅ **News & Sentiment**
        - Real-time news articles from multiple sources
        - Automatic sentiment classification (Positive, Neutral, Negative)
        - Sentiment distribution analysis
        - Article summaries and source attribution
        
        ✅ **Macroeconomic Context**
        - Federal Funds Rate
        - Treasury yields (10-year)
        - Inflation (CPI) data
        - Unemployment rate
        - VIX volatility index
        - Macro impact analysis on sectors
        
        ✅ **Risk Analysis**
        - Company-specific risk identification
        - Sector and market risks
        - Macro-economic risks
        - Valuation and leverage risks
        - Risk severity classification
        - Detailed risk explanations
        
        ✅ **Professional Investment Memo**
        - AI-generated analyst-style memo
        - Executive summary
        - Financial analysis
        - Market performance review
        - Risk assessment
        - Bull/Base/Bear case scenarios
        - Investment recommendations
        - Professional formatting and disclaimers
        
        ✅ **Company Overview**
        - Company name and sector
        - Market capitalization
        - Industry and employee count
        - 52-week price range
        - Business summary
        
        ### Development Roadmap
        
        **Phase 1:** ✅ Project skeleton and setup
        **Phase 2:** ✅ Market data & fundamentals agents
        **Phase 3:** ✅ News, macro agents, and dashboard pages
        **Phase 4:** ✅ Risk agent, report generation, final memo
        **Phase 5:** 🔄 Testing, refinement, deployment
        
        ### Technology Stack
        
        - **Framework:** Streamlit (web app)
        - **Data Processing:** Pandas, NumPy
        - **Financial Data:** yfinance
        - **News Data:** feedparser (Google News RSS)
        - **Visualization:** Plotly
        - **Language:** Python 3.12
        - **LLM:** OpenAI API (GPT-3.5-turbo)
        - **Agents:** Custom multi-agent architecture
        
        ### Core Agents (8 Total)
        
        1. **Market Data Agent** - Stock prices, returns, volatility ✅
        2. **Fundamentals Agent** - Balance sheet, ratios, profitability ✅
        3. **News Agent** - Headlines, sentiment analysis ✅
        4. **Macro Agent** - Economic indicators, macro impact ✅
        5. **Risk Agent** - Risk identification and scoring ✅
        6. **Report Agent** - Final memo generation ✅
        7. **SEC Agent** - Filing analysis (Ready for Phase 5)
        8. **Critic Agent** - Quality validation (Ready for Phase 5)
        
        ### Features Demonstrated
        
        ✅ Agentic AI Architecture
        ✅ Multi-source Data Integration
        ✅ LLM-based Analysis
        ✅ Financial Calculations
        ✅ Sentiment Analysis
        ✅ Risk Assessment
        ✅ Professional Reporting
        ✅ Streamlit Dashboard
        ✅ API Integration
        ✅ Error Handling & Logging
        
        ### Not a Prediction Tool
        
        This is **not** a stock price prediction application. Instead, it focuses on:
        - Financial research automation
        - Information synthesis and visualization
        - Risk analysis and explanation
        - Decision support (not decision making)
        - Professional analyst-style reporting
        
        ### Skills Demonstrated
        
        - **AI/ML:** Multi-agent systems, LLM integration, prompt engineering
        - **Finance:** Fundamental analysis, risk assessment, research methodology
        - **Data Engineering:** API integration, data aggregation, processing
        - **Software Engineering:** Modular architecture, error handling, logging
        - **Product Development:** User experience, dashboard design, reporting
        
        ### Disclaimer
        
        Educational and portfolio purposes only.
        Not investment advice.
        Always consult qualified financial professionals.
        
        ### Contact & Credits
        
        **Project:** Agentic AI Capital Markets Research Analyst
        **Built with:** Python, Streamlit, OpenAI, yfinance
        **Purpose:** Portfolio demonstration for AI/Data Science roles
        """)


def main():
    """Main application entry point"""
    
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div class="aa-brand">
            <div class="brand-name">📊 AI Analyst</div>
            <div class="brand-tag">Institutional Research Platform</div>
        </div>
        """, unsafe_allow_html=True)

        page = st.radio(
            "Navigation",
            [
                "Home",
                "Company Overview",
                "Market Performance",
                "Fundamentals",
                "Peer Comparison",
                "News & Sentiment",
                "Macro Environment",
                "Risk Analysis",
                "Research Memo",
                "About"
            ],
            label_visibility="collapsed"
        )

        render_market_status()
    
    # Main content
    if page == "Home":
        show_home_page()
    elif page == "Company Overview":
        show_company_overview()
    elif page == "Market Performance":
        show_market_performance()
    elif page == "Fundamentals":
        show_fundamentals()
    elif page == "Peer Comparison":
        show_peer_comparison()
    elif page == "News & Sentiment":
        show_news_sentiment()
    elif page == "Macro Environment":
        show_macro_environment()
    elif page == "Risk Analysis":
        show_risk_analysis()
    elif page == "Research Memo":
        show_research_memo()
    else:  # About
        show_about()


if __name__ == "__main__":
    main()