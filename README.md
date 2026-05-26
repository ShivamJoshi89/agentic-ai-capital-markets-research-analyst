# Agentic AI Capital Markets Research Analyst

A multi-agent AI system that automates equity research by analyzing stock prices, company fundamentals, SEC filings, news sentiment, and macroeconomic indicators to generate analyst-style investment research memos.

## Project Status

**Phase 1: Project Skeleton** ✅

Current development status: Building core infrastructure and agent framework.

## Quick Start

### Prerequisites
- Python 3.9 or higher
- OpenAI API key (or Claude API key)
- Windows, Mac, or Linux

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

5. **Run the app:**
```bash
   streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

## Features

### MVP (In Development)
- ✅ Ticker input
- ✅ yfinance stock data integration
- ✅ Company overview
- ✅ Historical price charts
- ✅ Return calculations (1M, 3M, 6M)
- ✅ Volatility & moving averages
- ✅ Maximum drawdown
- ✅ Financial fundamentals
- ✅ Recent news collection
- ✅ Risk analysis
- ✅ AI-generated research memo
- ✅ Streamlit dashboard

### Good-to-Have
- 🔄 SEC EDGAR integration
- 🔄 FRED macroeconomic data
- 🔄 Source citations
- 🔄 Confidence scoring
- 🔄 PDF export

## Project Structure

agentic-ai-capital-markets-research-analyst/
├── app.py                          # Streamlit main application
├── requirements.txt                # Project dependencies
├── .env.example                    # Example environment variables
├── .gitignore                      # Git ignore rules
├── README.md                       # This file
│
├── data/                           # Data storage
│   ├── raw/                        # Raw data from APIs
│   │   ├── stock_prices/
│   │   ├── fundamentals/
│   │   ├── news/
│   │   └── macro/
│   ├── processed/                  # Processed data
│   │   ├── market_metrics/
│   │   ├── financial_ratios/
│   │   └── research_inputs/
│   └── reports/                    # Generated reports
│       └── generated_memos/
│
├── src/                            # Source code
│   ├── agents/                     # AI agents
│   │   ├── init.py
│   │   ├── market_data_agent.py
│   │   ├── fundamentals_agent.py
│   │   ├── sec_filing_agent.py
│   │   ├── news_agent.py
│   │   ├── macro_agent.py
│   │   ├── risk_agent.py
│   │   ├── report_agent.py
│   │   └── critic_agent.py
│   │
│   ├── data_sources/               # Data source integrations
│   │   ├── init.py
│   │   ├── yfinance_client.py
│   │   ├── sec_edgar_client.py
│   │   ├── news_client.py
│   │   └── fred_client.py
│   │
│   ├── analytics/                  # Financial calculations
│   │   ├── init.py
│   │   ├── technical_indicators.py
│   │   ├── financial_ratios.py
│   │   ├── risk_metrics.py
│   │   └── sentiment_analysis.py
│   │
│   ├── prompts/                    # LLM prompts
│   │   ├── research_memo_prompt.txt
│   │   ├── news_summary_prompt.txt
│   │   ├── risk_analysis_prompt.txt
│   │   ├── macro_summary_prompt.txt
│   │   └── critic_prompt.txt
│   │
│   ├── reports/                    # Report generation
│   │   ├── init.py
│   │   ├── memo_template.py
│   │   └── export_report.py
│   │
│   └── utils/                      # Utilities
│       ├── init.py
│       ├── config.py
│       ├── helpers.py
│       └── logger.py
│
├── notebooks/                      # Jupyter notebooks
│   ├── 01_market_data_exploration.ipynb
│   ├── 02_fundamentals_exploration.ipynb
│   └── 03_news_sentiment_exploration.ipynb
│
├── outputs/                        # Generated outputs
│   ├── sample_memos/
│   ├── charts/
│   └── screenshots/
│
└── tests/                          # Unit tests
├── test_market_data_agent.py
├── test_risk_metrics.py
└── test_financial_ratios.py

## Technology Stack

- **Language:** Python 3.9+
- **Web Framework:** Streamlit
- **Data Processing:** Pandas, NumPy
- **Visualization:** Plotly, Matplotlib
- **Financial Data:** yfinance
- **LLM Integration:** OpenAI API
- **News Parsing:** feedparser, BeautifulSoup4
- **Testing:** pytest

## Core Agents

1. **Market Data Agent** - Stock prices, returns, volatility
2. **Financial Fundamentals Agent** - Company financials and ratios
3. **SEC Filing Agent** - Official SEC data
4. **News Agent** - Recent news and sentiment
5. **Macro Agent** - Economic indicators
6. **Risk Agent** - Key risk identification
7. **Report Generation Agent** - Investment memo creation
8. **Critic/Validation Agent** - Output quality review

## Data Sources

- **yfinance:** Stock prices, company info, financials
- **SEC EDGAR API:** Official filing data
- **NewsAPI / RSS:** Company news
- **FRED API:** Macroeconomic indicators

## Development Status

- Phase 1: ✅ Project skeleton and setup
- Phase 2: 🔄 Core agents and data pipeline
- Phase 3: 🔄 LLM integration and memo generation
- Phase 4: 🔄 Dashboard UI and refinement
- Phase 5: 🔄 Testing, documentation, deployment

## Roadmap

**Week 1:** Project setup, market data agent, fundamentals agent
**Week 2:** News agent, macro agent, risk agent
**Week 3:** Report generation, dashboard, testing, demo

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

[Your Name] - [Your Email] - [GitHub Profile]

## Acknowledgments

- yfinance for financial data
- Streamlit for dashboard framework
- OpenAI for LLM capabilities
- Financial research best practices from investment institutions