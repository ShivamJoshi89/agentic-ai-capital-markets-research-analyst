"""
Agentic AI Capital Markets Research Analyst
Main Streamlit application
"""

import streamlit as st
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

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
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)


def main():
    """Main application entry point"""
    
    # Sidebar
    with st.sidebar:
        st.title("🤖 AI Analyst")
        page = st.radio(
            "Navigation",
            ["Home", "Research Memo", "About"]
        )
    
    # Main content
    if page == "Home":
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
            2. Click "Generate Research Memo"
            3. Review the comprehensive analyst-style report
            
            ---
            """)
        
        # Input section
        col1, col2 = st.columns([3, 1])
        
        with col1:
            ticker = st.text_input(
                "Enter Stock Ticker",
                placeholder="e.g., JPM, AAPL, NVDA, MS",
                key="ticker_input"
            )
        
        with col2:
            generate_button = st.button(
                "🔍 Generate Memo",
                key="generate_button",
                use_container_width=True
            )
        
        if generate_button:
            if not ticker:
                st.warning("⚠️ Please enter a stock ticker")
            else:
                st.info(f"🔄 Generating research memo for {ticker.upper()}...")
                st.info("Phase 1: Project skeleton created. Phase 2 implementation coming soon.")
        
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
    
    elif page == "Research Memo":
        st.title("📋 Investment Research Memo")
        st.info("Memo generation coming in Phase 2. Enter a ticker on the Home page.")
        
        st.markdown("""
            ### Memo Structure
            
            The final memo will include:
            1. Executive Summary
            2. Company Overview
            3. Market Performance
            4. Financial Fundamentals
            5. News & Sentiment
            6. Macro Context
            7. Key Risks
            8. Bull/Base/Bear Cases
            9. Final Summary
            """)
    
    else:  # About
        st.title("ℹ️ About This Project")
        
        st.markdown("""
            ## Agentic AI Capital Markets Research Analyst
            
            ### Project Vision
            
            This project demonstrates how AI agents can automate financial research workflows
            to support investment decision-making.
            
            ### Key Capabilities
            
            - **Automated Research:** Collects financial data from multiple sources
            - **Multi-Agent System:** Specialized agents for different analytical tasks
            - **Risk Analysis:** Identifies and explains key risks
            - **Analyst-Style Reporting:** Generates professional investment memos
            - **Explainable AI:** Shows reasoning, cites sources, highlights uncertainty
            
            ### Not a Prediction Tool
            
            This is **not** a stock price prediction application. Instead, it focuses on:
            - Financial research automation
            - Information synthesis
            - Risk analysis and explanation
            - Decision support (not decision making)
            
            ### Technology
            
            - Python, Streamlit, Pandas, NumPy
            - yfinance, SEC EDGAR, NewsAPI
            - OpenAI API for LLM-based analysis
            
            ### Portfolio Project
            
            Built for demonstrating skills in:
            - Agentic AI design
            - Financial analysis
            - LLM integration
            - Data engineering
            - Dashboard development
            
            ### Disclaimer
            
            Educational and portfolio purposes only.
            Not investment advice.
            Always consult qualified professionals.
            """)
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("📊 [GitHub](https://github.com)")
        with col2:
            st.info("💼 [Portfolio](https://example.com)")
        with col3:
            st.info("📧 [Contact](mailto:your@email.com)")


if __name__ == "__main__":
    main()