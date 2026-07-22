"""
FastAPI backend for the Agentic AI Capital Markets Research Analyst.

Exposes the existing agent pipeline as REST endpoints for external frontends
(e.g. React). Runs alongside the Streamlit app without modifying it:

    streamlit run app.py                    # UI on :8501
    python api.py                           # API on :8000
    (or: uvicorn api:app --port 8000)
"""

import logging
import math
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add src to path (same convention as app.py)
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.market_data_agent import MarketDataAgent
from agents.fundamentals_agent import FinancialsAgent
from agents.news_agent import NewsAgent
from agents.macro_agent import MacroAgent
from agents.risk_agent import RiskAgent
from agents.report_agent import ReportAgent
from agents.peer_agent import PeerComparisonAgent
from data_sources.yfinance_client import YFinanceClient
from utils.helpers import validate_ticker
from utils.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(
    title="AI Capital Markets Research Analyst API",
    description="REST API over the multi-agent equity research pipeline",
    version="1.0.0",
)

# CORS for browser frontends (dev-friendly: all origins).
# Tighten allow_origins to the deployed frontend URL for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    ticker: str


def to_jsonable(value):
    """Recursively convert pipeline output to JSON-safe types.

    Handles numpy scalars, NaN/inf (-> null), pandas Timestamps, and drops
    any DataFrame/Series that was not explicitly transformed upstream.
    """
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, (pd.DataFrame, pd.Series)):
        return None
    return value


def history_to_records(history: pd.DataFrame) -> list:
    """Convert the yfinance price history DataFrame to compact JSON records"""
    if history is None or not isinstance(history, pd.DataFrame) or history.empty:
        return []
    records = []
    for idx, row in history.iterrows():
        close = row.get("Close")
        volume = row.get("Volume")
        records.append({
            "date": idx.strftime("%Y-%m-%d"),
            "close": round(float(close), 2) if pd.notna(close) else None,
            "volume": int(volume) if pd.notna(volume) else None,
        })
    return records


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    """Run the full agent pipeline for a ticker and return all results.

    Mirrors the stage order of the Streamlit app's fetch_analysis().
    Synchronous by design - the pipeline takes ~30-60s including the LLM memo.
    """
    ticker = request.ticker.upper().strip()

    if not validate_ticker(ticker):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid ticker format: '{request.ticker}'. Expected 1-5 letters (e.g. JPM)."
        )

    logger.info(f"API analysis requested for {ticker}")

    try:
        company_info = YFinanceClient().get_company_info(ticker)
        if not company_info or not company_info.get("success"):
            raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")

        market_data = MarketDataAgent().run(ticker)
        if not market_data.get("success"):
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch market data for {ticker}: {market_data.get('error')}"
            )

        # Replace the raw DataFrame with JSON-friendly records
        price_history = history_to_records(market_data.pop("data", None))

        fundamentals_data = FinancialsAgent().run(ticker)

        news_data = NewsAgent().run(ticker, company_info.get("company_name", ticker))
        if not news_data.get("success"):
            news_data = {"success": False, "articles": []}

        macro_data = MacroAgent().run(ticker=ticker, sector=company_info.get("sector"))
        if not macro_data.get("success"):
            macro_data = {"success": False}

        peer_data = PeerComparisonAgent().run(ticker)
        if not peer_data.get("success"):
            peer_data = {"success": False}

        all_analysis_data = {
            "market_data": market_data,
            "fundamentals_data": fundamentals_data,
            "news_data": news_data,
            "company_info": company_info,
            "macro_data": macro_data,
        }
        risk_data = RiskAgent().run(ticker, all_analysis_data)
        if not risk_data.get("success"):
            risk_data = {"success": False, "risks": [], "special_situations": []}

        all_analysis_data["risk_data"] = risk_data
        memo_data = ReportAgent().run(ticker, all_analysis_data)

        return to_jsonable({
            "ticker": ticker,
            "success": True,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "company_info": company_info,
            "market_data": market_data,
            "price_history": price_history,
            "fundamentals_data": fundamentals_data,
            "news_data": news_data,
            "macro_data": macro_data,
            "peer_data": peer_data,
            "risk_data": risk_data,
            "memo_data": memo_data,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API analysis failed for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
