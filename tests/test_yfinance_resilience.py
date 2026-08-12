"""
Tests for YFinanceClient's rate-limit resilience: retry with exponential
backoff, and a clear surfaced error (not a silent None) once retries are
exhausted. time.sleep is stubbed so the backoff doesn't slow the suite.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import data_sources.yfinance_client as yfinance_client_module
from data_sources.yfinance_client import YFinanceClient
from yfinance.exceptions import YFRateLimitError
from agents.fundamentals_agent import FinancialsAgent


@pytest.fixture(autouse=True)
def _no_backoff_sleep(monkeypatch):
    """Never actually sleep during the backoff in tests."""
    monkeypatch.setattr(yfinance_client_module.time, "sleep", lambda _s: None)


def test_fetch_with_retry_recovers_after_transient_rate_limit():
    """A rate-limit that clears within the cap must be retried and succeed -
    a transient throttle should not become a hard failure."""
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise YFRateLimitError()
        return "OK"

    assert YFinanceClient._fetch_with_retry(flaky, "test") == "OK"
    assert calls["n"] == 3  # two retries then success


def test_fetch_with_retry_raises_after_exhaustion():
    """Persistent throttling must surface as YFRateLimitError after the cap,
    not be swallowed - the caller needs to know it was rate-limited."""
    calls = {"n": 0}

    def always():
        calls["n"] += 1
        raise YFRateLimitError()

    with pytest.raises(YFRateLimitError):
        YFinanceClient._fetch_with_retry(always, "test")
    assert calls["n"] == YFinanceClient.RATE_LIMIT_MAX_RETRIES  # capped, not infinite


def test_fetch_with_retry_does_not_retry_non_rate_limit_errors():
    """Only rate-limit errors are retried; a genuine error propagates at once
    (retrying it would just waste time and hide the real problem)."""
    calls = {"n": 0}

    def other():
        calls["n"] += 1
        raise ValueError("genuine error")

    with pytest.raises(ValueError):
        YFinanceClient._fetch_with_retry(other, "test")
    assert calls["n"] == 1  # not retried


class _RateLimitedTicker:
    @property
    def info(self):
        raise YFRateLimitError()


def test_get_fundamentals_surfaces_rate_limit_instead_of_none(monkeypatch):
    """get_fundamentals must RAISE on exhausted rate-limit, not return None -
    None would be indistinguishable from 'this ticker has no data'."""
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: _RateLimitedTicker())
    with pytest.raises(YFRateLimitError):
        YFinanceClient().get_fundamentals("FAKE")


def test_fundamentals_agent_reports_rate_limit_in_error_field(monkeypatch):
    """End-to-end: the agent layer turns the surfaced rate-limit into a clear
    error message rather than the generic 'Failed to fetch fundamentals'."""
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: _RateLimitedTicker())
    result = FinancialsAgent().run("FAKE")
    assert result["success"] is False
    assert "rate limit" in result["error"].lower() or "too many requests" in result["error"].lower()
