"""
FastAPI backend for the Agentic AI Capital Markets Research Analyst.

Exposes the agent pipeline as REST endpoints for the React frontend:

    python api.py                           # API on :8000
    (or: uvicorn api:app --port 8000)
"""

import json
import logging
import math
import os
import sys
import threading
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.market_data_agent import MarketDataAgent
from agents.fundamentals_agent import FinancialsAgent
from agents.news_agent import NewsAgent
from agents.macro_agent import MacroAgent
from agents.risk_agent import RiskAgent
from agents.report_agent import ReportAgent
from agents.peer_agent import PeerComparisonAgent
from agents.financing_risk_agent import FinancingRiskAgent
from data_sources.yfinance_client import YFinanceClient
from utils.helpers import validate_ticker
from utils.logger import setup_logger

logger = setup_logger(__name__)

# --- Deployment configuration (all env-driven so nothing sensitive is baked in) ---
IS_PRODUCTION = os.getenv("APP_ENV", "development").lower() == "production"

# CORS: comma-separated allowed origins. Defaults to the local Vite/CRA dev
# ports; in production this MUST be set to the real frontend origin(s) (the
# Vercel domain) - never left as a wildcard for a credentialed public API.
_cors_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]

# Global daily cap on full analyses (each one triggers a paid LLM memo). This
# is the second layer beyond per-IP limiting: a single actor rotating IPs can
# defeat per-IP limits, but this bounds worst-case spend regardless. In-memory
# (fine for a single-worker deployment; use a shared store if scaled out).
MEMO_DAILY_CAP = int(os.getenv("MEMO_DAILY_CAP", "200"))


# Number of trusted proxies in front of the app (Railway's edge = 1). Each
# proxy APPENDS the address it received the request from, so the real client IP
# is the entry THIS many positions from the RIGHT of X-Forwarded-For - the
# value our trusted proxy added - NOT the leftmost value, which is fully
# client-controllable and was trivially spoofable (rotating it gave a fresh
# rate-limit bucket per request). Must match the real topology: if Railway adds
# more internal hops, bump TRUSTED_PROXY_COUNT; verify on the deployed instance.
TRUSTED_PROXY_COUNT = int(os.getenv("TRUSTED_PROXY_COUNT", "1"))


def _client_ip(request: Request) -> str:
    """Rate-limit key: the client IP as seen by our trusted proxy layer.
    Takes the Nth-from-rightmost X-Forwarded-For entry (N = TRUSTED_PROXY_COUNT)
    so an attacker-supplied left prefix is ignored, and falls back to the socket
    peer when the header is absent or shorter than expected."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if len(parts) >= TRUSTED_PROXY_COUNT:
            return parts[-TRUSTED_PROXY_COUNT]
    return get_remote_address(request)


def _analyze_rate_limit() -> str:
    """Per-IP limit for the analyze endpoint, read per-request so it's tunable
    via env without a code change (default: 5 requests/minute/IP)."""
    return os.getenv("ANALYZE_RATE_LIMIT", "5/minute")


limiter = Limiter(key_func=_client_ip)

app = FastAPI(
    title="AI Capital Markets Research Analyst API",
    description="REST API over the multi-agent equity research pipeline",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --- Global daily memo cap (thread-safe, resets at UTC midnight) ---
#
# Optional on-disk persistence so the counter survives a process restart (a
# crash or worker recycle) rather than silently resetting "200/day" to "200
# since last restart". Durability guarantee, stated honestly:
#   - DAILY_CAP_STATE_FILE unset (default): in-memory only; ANY restart resets.
#   - set to a path on the ephemeral container FS: survives an in-container
#     process restart, but a redeploy / container replacement still resets it.
#   - set to a path on a mounted Railway Volume: fully durable across redeploys.
# In all cases this assumes a SINGLE instance (see deploy notes) - the counter
# is per-process/per-file, not coordinated across replicas.
DAILY_CAP_STATE_FILE = os.getenv("DAILY_CAP_STATE_FILE", "")
_daily_lock = threading.Lock()
_daily_quota = {"date": None, "count": 0}


def _read_quota_state() -> dict:
    """Current {date, count}, from the state file when configured (the source
    of truth across restarts), else the in-memory mirror. Missing/corrupt file
    is treated as a fresh day."""
    if DAILY_CAP_STATE_FILE:
        try:
            with open(DAILY_CAP_STATE_FILE) as f:
                data = json.load(f)
            if isinstance(data, dict) and "count" in data:
                return {"date": data.get("date"), "count": int(data.get("count", 0))}
        except (OSError, ValueError, TypeError):
            pass
        return {"date": None, "count": 0}
    return dict(_daily_quota)


def _write_quota_state(state: dict) -> None:
    _daily_quota.update(state)
    if DAILY_CAP_STATE_FILE:
        try:
            with open(DAILY_CAP_STATE_FILE, "w") as f:
                json.dump(state, f)
        except OSError as e:
            logger.warning(f"Could not persist daily quota to {DAILY_CAP_STATE_FILE}: {e}")


def _consume_daily_quota() -> bool:
    """Reserve one unit of the global daily analysis quota. Returns False if
    the cap is already reached for the current UTC day."""
    today = datetime.now(timezone.utc).date().isoformat()
    with _daily_lock:
        state = _read_quota_state()
        if state.get("date") != today:
            state = {"date": today, "count": 0}
        if state["count"] >= MEMO_DAILY_CAP:
            _write_quota_state(state)
            return False
        state["count"] += 1
        _write_quota_state(state)
        return True


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
@limiter.limit(_analyze_rate_limit)
def analyze(request: Request, payload: AnalyzeRequest):
    """Run the full agent pipeline for a ticker and return all results.

    Synchronous by design - the pipeline takes ~30-60s including the LLM memo.
    Protected by per-IP rate limiting (see _analyze_rate_limit) plus a global
    daily cap on paid memo generations.
    """
    ticker = payload.ticker.upper().strip()

    # Validate the only user-supplied parameter BEFORE it reaches any external
    # call (yfinance/SEC/OpenAI). Rejects anything but 1-5 uppercase letters.
    if not validate_ticker(ticker):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid ticker format: '{payload.ticker}'. Expected 1-5 letters (e.g. JPM)."
        )

    # Second cost-protection layer: bound worst-case daily LLM spend regardless
    # of per-IP limits. Checked after validation so a bad ticker can't burn the
    # quota, and before the pipeline so the paid work never runs once exhausted.
    if not _consume_daily_quota():
        raise HTTPException(
            status_code=429,
            detail=f"Daily analysis limit ({MEMO_DAILY_CAP}) reached. Please try again tomorrow."
        )

    logger.info(f"API analysis requested for {ticker}")

    try:
        company_info = YFinanceClient().get_company_info(ticker)
        if not company_info or not company_info.get("success"):
            raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")

        market_data = MarketDataAgent().run(ticker)
        if not market_data.get("success"):
            detail = f"Failed to fetch market data for {ticker}"
            if not IS_PRODUCTION:
                detail += f": {market_data.get('error')}"
            raise HTTPException(status_code=502, detail=detail)

        # Replace the raw DataFrame with JSON-friendly records
        price_history = history_to_records(market_data.pop("data", None))

        fundamentals_data = FinancialsAgent().run(ticker)

        financing_data = FinancingRiskAgent().run(
            ticker, fundamentals_data=fundamentals_data, company_info=company_info
        )
        if not financing_data.get("success"):
            financing_data = {
                "success": False, "flags": [], "overhang_level": "Unknown",
                "dilution": {"available": False}, "cash_runway": {"available": False},
                "financing_filings": [],
            }

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
            "financing_data": financing_data,
        }
        risk_data = RiskAgent().run(ticker, all_analysis_data)
        if not risk_data.get("success"):
            risk_data = {"success": False, "risks": [], "special_situations": []}

        all_analysis_data["risk_data"] = risk_data
        memo_data = ReportAgent().run(ticker, all_analysis_data)

        return to_jsonable({
            "ticker": ticker,
            "success": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "company_info": company_info,
            "market_data": market_data,
            "price_history": price_history,
            "fundamentals_data": fundamentals_data,
            "news_data": news_data,
            "macro_data": macro_data,
            "peer_data": peer_data,
            "financing_data": financing_data,
            "risk_data": risk_data,
            "memo_data": memo_data,
        })

    except HTTPException:
        raise
    except Exception as e:
        # Full detail to server logs only; never leak internals (stack traces,
        # library messages) to a public client in production.
        logger.error(f"API analysis failed for {ticker}: {str(e)}", exc_info=True)
        detail = "Analysis failed due to an internal error." if IS_PRODUCTION else f"Analysis failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
