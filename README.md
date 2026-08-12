# Agentic AI Capital Markets Research Analyst

A multi-agent AI system that automates equity research by analyzing stock prices, company fundamentals, financing/dilution risk, news sentiment, peer valuation, and macroeconomic indicators to generate analyst-style investment research memos.

## Quick Start

### Prerequisites
- Python 3.9 or higher
- Node.js 18+ (for the frontend)
- OpenAI API key

### Installation

1. **Clone the repository:**
```bash
   git clone https://github.com/YOUR_USERNAME/agentic-ai-capital-markets-research-analyst.git
   cd agentic-ai-capital-markets-research-analyst
```

2. **Create virtual environment:**
```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Mac/Linux
```

3. **Install dependencies:**
```bash
   pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
   cp .env.example .env
   # Edit .env and add your API keys
```

5. **Run the backend API (port 8000):**
```bash
   python api.py
```

6. **Run the frontend (port 3000), in a separate terminal:**
```bash
   cd frontend
   npm install
   npm run dev
```

The app will open at `http://localhost:3000`.

## Features

- ✅ Ticker input
- ✅ yfinance stock data integration
- ✅ Company overview
- ✅ Historical price charts
- ✅ Return calculations (1M, 3M, 6M, YTD)
- ✅ Volatility & moving averages
- ✅ Maximum drawdown
- ✅ Financial fundamentals
- ✅ Recent news collection & sentiment
- ✅ Peer comparison & relative valuation
- ✅ Financing & dilution risk (SEC EDGAR)
- ✅ Live macroeconomic data (FRED)
- ✅ Risk analysis
- ✅ AI-generated research memo
- ✅ PDF export of the research memo (client-side, via jsPDF)

### Why a Financing & Dilution Risk Agent

Most retail-facing stock tools focus on P/E ratios and technicals. For
small/micro-cap issuers, an equally important signal lives in the SEC filing
index and the share count itself: shelf registrations, at-the-market (ATM)
programs, and committed equity lines ("common stock purchase agreements")
that dilute holders regardless of operating performance. This module tracks
trailing share-count growth, estimates cash runway from operating burn, and
flags recent financing-related filings, rolling all three into a single
overhang score.

## Project Structure

agentic-ai-capital-markets-research-analyst/
├── api.py                          # FastAPI backend - exposes the agent pipeline as REST endpoints
├── requirements.txt                # Python dependencies
├── .env.example                    # Example environment variables
├── .gitignore                      # Git ignore rules
├── README.md                       # This file
│
├── src/                            # Python source (agent pipeline)
│   ├── agents/                     # AI agents
│   │   ├── __init__.py
│   │   ├── market_data_agent.py
│   │   ├── fundamentals_agent.py
│   │   ├── financing_risk_agent.py
│   │   ├── news_agent.py
│   │   ├── macro_agent.py
│   │   ├── peer_agent.py
│   │   ├── risk_agent.py
│   │   └── report_agent.py
│   │
│   ├── data_sources/               # Data source integrations
│   │   ├── __init__.py
│   │   ├── yfinance_client.py
│   │   ├── sec_edgar_client.py
│   │   ├── news_client.py
│   │   └── fred_client.py
│   │
│   ├── analytics/                  # Financial calculations
│   │   ├── __init__.py
│   │   ├── technical_indicators.py
│   │   ├── financial_ratios.py
│   │   └── risk_metrics.py
│   │
│   ├── prompts/                    # LLM prompts
│   │   └── research_memo_prompt.txt
│   │
│   └── utils/                      # Utilities
│       ├── __init__.py
│       ├── config.py
│       ├── helpers.py
│       └── logger.py
│
├── frontend/                        # React + Vite frontend (the only UI)
│   └── src/
│       ├── pages/
│       │   ├── Home.jsx             # Ticker search / landing page
│       │   └── Dashboard.jsx        # Sidebar + page-switching shell
│       ├── components/
│       │   ├── pages/                # Dashboard sub-pages
│       │   │   ├── Overview.jsx
│       │   │   ├── MarketPerformance.jsx
│       │   │   ├── Fundamentals.jsx
│       │   │   ├── PeerComparison.jsx
│       │   │   ├── NewsSentiment.jsx
│       │   │   ├── MacroEnvironment.jsx
│       │   │   ├── RiskAnalysis.jsx
│       │   │   ├── ResearchMemo.jsx
│       │   │   └── About.jsx
│       │   ├── AnimatedNumber.jsx
│       │   ├── MetricCard.jsx
│       │   ├── PriceChart.jsx
│       │   └── LoadingPipeline.jsx
│       ├── api/client.js            # Fetch wrapper for the FastAPI backend
│       ├── hooks/useCountUp.js
│       └── utils/format.js
│
└── tests/                          # Unit tests
    └── test_financing_risk_agent.py

## Technology Stack

- **Backend Language:** Python 3.9+
- **API Framework:** FastAPI
- **Frontend:** React + Vite, Tailwind CSS, Framer Motion
- **Data Processing:** Pandas, NumPy
- **Financial Data:** yfinance
- **LLM Integration:** OpenAI API
- **News Parsing:** feedparser, BeautifulSoup4
- **PDF Export:** jsPDF (client-side)
- **Testing:** pytest

## Core Agents

The agents run in this order for each analysis (see `api.py`):

1. **Market Data Agent** - Stock prices, returns, volatility, moving averages, drawdown
2. **Fundamentals Agent** - Income statement, balance sheet, profitability, valuation ratios
3. **Financing & Dilution Risk Agent** - SEC EDGAR-based dilution tracking, cash runway estimation, and financing-filing detection
4. **News Agent** - Recent news and keyword-based sentiment classification
5. **Macro Agent** - Fed funds rate, treasury yields, CPI inflation, unemployment, VIX (from FRED)
6. **Peer Comparison Agent** - Comparable-company selection and relative valuation
7. **Risk Agent** - Consolidates valuation, leverage, market, macro, sentiment, and sector risks
8. **Report Generation Agent** - Synthesizes all of the above into a narrative investment memo

## Data Sources

- **yfinance:** Stock prices, company info, financials
- **SEC EDGAR API:** Ticker-to-CIK resolution, shares-outstanding history, and recent filings. No API key required, but a descriptive User-Agent is mandatory per SEC's fair-access policy.
- **Google News RSS:** Company news headlines (via `feedparser`)
- **FRED API:** Macroeconomic indicators
- **OpenAI API:** Research memo generation

## Resume Bullet Points

- Built a multi-agent AI research platform combining stock prices, company fundamentals, news sentiment, and macro indicators to generate analyst-style investment memos
- Designed modular agent architecture with specialized responsibilities for financial data collection, analysis, and reasoning
- Implemented financial metrics including returns, volatility, moving averages, maximum drawdown, and valuation ratios
- Integrated LLM-based report generation with risk-aware prompts for explainable financial analysis

## Disclaimer

This project is for educational and portfolio purposes only. It does not provide investment advice, trading recommendations, or financial guidance. All outputs should be reviewed by qualified professionals before use.

## License

MIT License - see LICENSE file for details

## Contact

Shivam Joshi - joshishivam047@gmail.com

## Acknowledgments

- yfinance for financial data
- OpenAI for LLM capabilities
- Financial research best practices from investment institutions