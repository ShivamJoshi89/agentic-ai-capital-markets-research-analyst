"""
Agentic AI Capital Markets Research Analyst
Main Streamlit application - Phase 3
"""

import streamlit as st
import sys
from pathlib import Path
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.market_data_agent import MarketDataAgent
from agents.fundamentals_agent import FinancialsAgent
from agents.news_agent import NewsAgent
from agents.macro_agent import MacroAgent
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

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .metric-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
    }
    .news-article {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #007bff;
    }
    .sentiment-positive {
        color: #28a745;
        font-weight: bold;
    }
    .sentiment-neutral {
        color: #ffc107;
        font-weight: bold;
    }
    .sentiment-negative {
        color: #dc3545;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)


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
    """Fetch market, fundamentals, news, and macro data for ticker"""
    
    ticker = ticker.upper().strip()
    
    # Validate ticker
    if not validate_ticker(ticker):
        st.error(f"❌ Invalid ticker format: '{ticker}'. Please enter 1-5 uppercase letters (e.g., JPM, AAPL)")
        return False
    
    try:
        with st.spinner(f"🔄 Fetching comprehensive analysis for {ticker}..."):
            # Fetch company info
            yfinance_client = YFinanceClient()
            company_info = yfinance_client.get_company_info(ticker)
            
            if not company_info or not company_info.get("success"):
                st.error(f"❌ Could not find ticker '{ticker}'. Please check the symbol and try again.")
                logger.error(f"Failed to fetch company info for {ticker}")
                return False
            
            # Fetch market data
            market_agent = MarketDataAgent()
            market_data = market_agent.run(ticker)
            
            if not market_data.get("success"):
                st.error(f"❌ Failed to fetch market data for {ticker}")
                logger.error(f"Market data fetch failed: {market_data.get('error')}")
                return False
            
            # Fetch fundamentals
            fundamentals_agent = FinancialsAgent()
            fundamentals_data = fundamentals_agent.run(ticker)
            
            if not fundamentals_data.get("success"):
                st.warning(f"⚠️ Some fundamentals data unavailable for {ticker}")
            
            # Fetch news
            news_agent = NewsAgent()
            company_name = company_info.get("company_name", ticker)
            news_data = news_agent.run(ticker, company_name)
            
            if not news_data.get("success"):
                st.warning(f"⚠️ Could not fetch news for {ticker}")
                news_data = {"success": False, "articles": []}
            
            # Fetch macro data
            macro_agent = MacroAgent()
            sector = company_info.get("sector", None)
            macro_data = macro_agent.run(ticker=ticker, sector=sector)
            
            if not macro_data.get("success"):
                st.warning(f"⚠️ Could not fetch macro data")
                macro_data = {"success": False}
            
            # Store in session state
            st.session_state.ticker = ticker
            st.session_state.market_data = market_data
            st.session_state.fundamentals_data = fundamentals_data
            st.session_state.company_info = company_info
            st.session_state.news_data = news_data
            st.session_state.macro_data = macro_data
            
            return True
    
    except Exception as e:
        st.error(f"❌ Error fetching data: {str(e)}")
        logger.error(f"Error in fetch_analysis: {str(e)}")
        return False


def show_home_page():
    """Display home page"""
    
    st.title("📊 Agentic AI Capital Markets Research Analyst")
    
    st.markdown("""
        ## Welcome to the AI-Powered Equity Research Platform
        
        This application automates the first layer of equity research by combining:
        - 📈 Stock market data and technical analysis
        - 💰 Company fundamentals and financial ratios
        - 📰 Recent news and sentiment analysis
        - 🏛️ SEC filing information
        - 🌍 Macroeconomic context
        - ⚠️ Risk identification and analysis
        
        ### How to Use
        
        1. Enter a stock ticker (e.g., JPM, AAPL, NVDA)
        2. Click "Generate Research Analysis"
        3. Review the comprehensive analyst-style report
        
        ---
        """)
    
    # Input section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        ticker_input = st.text_input(
            "Enter Stock Ticker",
            placeholder="e.g., JPM, AAPL, NVDA, MS",
            key="ticker_input"
        )
    
    with col2:
        generate_button = st.button(
            "🔍 Generate Analysis",
            key="generate_button",
            use_container_width=True
        )
    
    if generate_button:
        if not ticker_input:
            st.warning("⚠️ Please enter a stock ticker")
        else:
            success = fetch_analysis(ticker_input)
            if success:
                st.success(f"✅ Data fetched successfully for {ticker_input.upper()}!")
                st.rerun()
    
    # Show last analyzed ticker if available
    if st.session_state.ticker:
        st.markdown("---")
        st.markdown(f"### 📍 Last Analyzed: {st.session_state.ticker}")
        
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
    
    # Information boxes
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Agents", 8)
        st.caption("Market, Fundamentals, News, Macro, Risk, SEC, Report, Critic")
    
    with col2:
        st.metric("Data Sources", 4)
        st.caption("yfinance, SEC EDGAR, NewsAPI, FRED")
    
    with col3:
        st.metric("Features", 12)
        st.caption("Returns, Vol, MA, Fundamentals, Risks, Memo")


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
        st.metric("1-Month Return", f"{metrics.get('one_month_return', 'N/A')}%")
    
    with col3:
        st.metric("3-Month Return", f"{metrics.get('three_month_return', 'N/A')}%")
    
    with col4:
        st.metric("6-Month Return", f"{metrics.get('six_month_return', 'N/A')}%")
    
    # Technical metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("YTD Return", f"{metrics.get('ytd_return', 'N/A')}%")
    
    with col2:
        st.metric("Volatility (Annual)", f"{metrics.get('volatility', 'N/A')}%")
    
    with col3:
        st.metric("Max Drawdown", f"{metrics.get('max_drawdown', 'N/A')}%")
    
    with col4:
        st.metric("Avg Volume", f"{metrics.get('avg_volume', 'N/A'):,.0f}")
    
    # Moving averages
    st.subheader("📊 Moving Averages")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("20-Day MA", f"${metrics.get('ma_20', 'N/A')}")
    
    with col2:
        st.metric("50-Day MA", f"${metrics.get('ma_50', 'N/A')}")
    
    with col3:
        st.metric("200-Day MA", f"${metrics.get('ma_200', 'N/A')}")
    
    # Price chart
    if market_data.get("data") is not None:
        st.subheader("📉 Price Chart (1 Year)")
        
        import plotly.graph_objects as go
        
        data = market_data.get("data")
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["Close"],
            mode='lines',
            name='Close Price',
            line=dict(color='#1f77b4', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["Volume"],
            mode='lines',
            name='Volume',
            yaxis='y2',
            line=dict(color='#ff7f0e', width=1)
        ))
        
        fig.update_layout(
            title=f"{ticker} - 1 Year Price History",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            yaxis2=dict(title="Volume", overlaying="y", side="right"),
            hovermode="x unified",
            height=500
        )
        
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
    
    # Articles
    st.subheader(f"📋 Recent Headlines ({total_articles} articles)")
    
    articles = news_data.get("articles", [])
    
    if not articles:
        st.info("No recent articles found for this ticker.")
    else:
        for idx, article in enumerate(articles, 1):
            sentiment = article.get("sentiment", "Neutral")
            
            # Sentiment badge color
            if sentiment == "Positive":
                sentiment_class = "✅"
            elif sentiment == "Negative":
                sentiment_class = "❌"
            else:
                sentiment_class = "⚪"
            
            with st.container():
                col1, col2 = st.columns([0.1, 0.9])
                
                with col1:
                    st.write(sentiment_class)
                
                with col2:
                    st.markdown(f"**{article.get('title', 'N/A')}**")
                    st.caption(f"📅 {article.get('published_date', 'N/A')} | 📰 {article.get('source', 'N/A')}")
                    st.write(article.get("description", "")[:200] + "...")
                    st.markdown(f"[Read More →]({article.get('url', '#')})")
                
                st.markdown("---")


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


def show_research_memo():
    """Display research memo page"""
    
    st.title("📋 Investment Research Memo")
    
    if not st.session_state.ticker:
        st.info("Memo generation coming soon. Enter a ticker on the Home page to analyze.")
        return
    
    ticker = st.session_state.ticker
    
    st.markdown(f"""
        ### Agentic AI Research Memo: {ticker}
        
        **Phase 3 Status:** Market, Fundamentals, News, and Macro agents implemented ✅
        - Market Data Agent: Collecting price data, returns, volatility
        - Financial Fundamentals Agent: Analyzing balance sheet and ratios
        - News Agent: Sentiment analysis and headlines
        - Macro Agent: Economic indicators and context
        
        **Coming in Phase 4:**
        - Risk Agent: Risk identification and scoring
        - Report Generation: Full analyst memo with bull/base/bear cases
        - Critic Agent: Output validation and quality checks
        
        ---
        
        ### Data Available for {ticker}:
        
        ✅ **Market Data** - Stock prices, returns, volatility, moving averages
        ✅ **Company Fundamentals** - Revenue, margins, ratios, balance sheet
        ✅ **News & Sentiment** - Recent headlines with sentiment classification
        ✅ **Macro Context** - Interest rates, inflation, unemployment, Treasury yields
        
        **Next Steps:**
        Navigate to each dashboard page to view:
        1. **Company Overview** - Basic company information
        2. **Market Performance** - Stock price trends and technical metrics
        3. **Fundamentals** - Financial statements and ratios
        4. **News & Sentiment** - Recent articles with sentiment analysis
        5. **Macro Environment** - Economic indicators and impact analysis
        
        Phase 4 will synthesize all this data into a final investment research memo with 
        risk analysis, bull/base/bear case scenarios, and final recommendations.
        """)


def show_about():
    """Display about page"""
    
    st.title("ℹ️ About This Project")
    
    st.markdown("""
        ## Agentic AI Capital Markets Research Analyst
        
        ### Project Vision
        
        This project demonstrates how AI agents can automate financial research workflows
        to support investment decision-making.
        
        ### Current Capabilities (Phase 3)
        
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
        **Phase 4:** 🔄 Risk agent, report generation, final memo
        **Phase 5:** 🔄 Testing, deployment, refinement
        
        ### Technology Stack
        
        - **Framework:** Streamlit (web app)
        - **Data Processing:** Pandas, NumPy
        - **Financial Data:** yfinance
        - **News Data:** feedparser (Google News RSS)
        - **Visualization:** Plotly
        - **Language:** Python 3.12
        - **LLM:** OpenAI API (for future phases)
        
        ### Core Agents
        
        1. **Market Data Agent** - Stock prices, returns, volatility
        2. **Fundamentals Agent** - Balance sheet, ratios, profitability
        3. **News Agent** - Headlines, sentiment analysis
        4. **Macro Agent** - Economic indicators, macro impact
        5. **Risk Agent** - Risk identification (Phase 4)
        6. **Report Agent** - Final memo generation (Phase 4)
        7. **SEC Agent** - Filing analysis (Future)
        8. **Critic Agent** - Quality validation (Phase 4)
        
        ### Not a Prediction Tool
        
        This is **not** a stock price prediction application. Instead, it focuses on:
        - Financial research automation
        - Information synthesis and visualization
        - Risk analysis and explanation
        - Decision support (not decision making)
        
        ### Disclaimer
        
        Educational and portfolio purposes only.
        Not investment advice.
        Always consult qualified financial professionals.
        """)


def main():
    """Main application entry point"""
    
    # Sidebar
    with st.sidebar:
        st.title("🤖 AI Analyst")
        page = st.radio(
            "Navigation",
            [
                "Home",
                "Company Overview",
                "Market Performance",
                "Fundamentals",
                "News & Sentiment",
                "Macro Environment",
                "Research Memo",
                "About"
            ]
        )
    
    # Main content
    if page == "Home":
        show_home_page()
    elif page == "Company Overview":
        show_company_overview()
    elif page == "Market Performance":
        show_market_performance()
    elif page == "Fundamentals":
        show_fundamentals()
    elif page == "News & Sentiment":
        show_news_sentiment()
    elif page == "Macro Environment":
        show_macro_environment()
    elif page == "Research Memo":
        show_research_memo()
    else:  # About
        show_about()


if __name__ == "__main__":
    main()