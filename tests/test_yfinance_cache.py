"""
Tests for the short-TTL yfinance result cache: a repeat request for the same
ticker within the TTL must not hit yfinance again, but must refetch once the
TTL has elapsed. time.monotonic is stubbed with a controllable clock.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import data_sources.yfinance_client as yfinance_client_module
from data_sources.yfinance_client import YFinanceClient


class _CountingTicker:
    """A fake yfinance Ticker that counts how many times .info is fetched."""

    def __init__(self, counter):
        self._counter = counter

    @property
    def info(self):
        self._counter["fetches"] += 1
        return {
            "sector": "Technology", "totalRevenue": 1_000_000_000,
            "netIncomeToCommon": 150_000_000, "profitMargins": 0.15,
            "grossMargins": 0.4, "operatingMargins": 0.2, "marketCap": 10_000_000_000,
            "financialCurrency": "USD", "currency": "USD",
            "trailingEps": 1.0, "trailingPE": 10.0, "priceToBook": 1.5,
        }
    # statement attributes are absent -> _safe_statement returns None (graceful)


@pytest.fixture
def _controlled_clock(monkeypatch):
    clock = {"t": 1000.0}
    monkeypatch.setattr(yfinance_client_module.time, "monotonic", lambda: clock["t"])
    return clock


def test_repeat_request_within_ttl_does_not_refetch(monkeypatch, _controlled_clock):
    monkeypatch.setattr(YFinanceClient, "CACHE_TTL_SEC", 1800)
    counter = {"fetches": 0}
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: _CountingTicker(counter))

    client = YFinanceClient()
    client.get_fundamentals("AAPL")
    client.get_fundamentals("AAPL")  # within TTL -> served from cache

    assert counter["fetches"] == 1


def test_request_after_ttl_expiry_refetches(monkeypatch, _controlled_clock):
    monkeypatch.setattr(YFinanceClient, "CACHE_TTL_SEC", 1800)
    counter = {"fetches": 0}
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: _CountingTicker(counter))

    client = YFinanceClient()
    client.get_fundamentals("AAPL")
    assert counter["fetches"] == 1

    _controlled_clock["t"] += 2000  # advance past the 1800s TTL
    client.get_fundamentals("AAPL")
    assert counter["fetches"] == 2  # refetched


def test_different_tickers_cached_separately(monkeypatch, _controlled_clock):
    monkeypatch.setattr(YFinanceClient, "CACHE_TTL_SEC", 1800)
    counter = {"fetches": 0}
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: _CountingTicker(counter))

    client = YFinanceClient()
    client.get_fundamentals("AAPL")
    client.get_fundamentals("MSFT")  # different key -> its own fetch

    assert counter["fetches"] == 2


def test_ttl_zero_disables_cache(monkeypatch, _controlled_clock):
    monkeypatch.setattr(YFinanceClient, "CACHE_TTL_SEC", 0)
    counter = {"fetches": 0}
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: _CountingTicker(counter))

    client = YFinanceClient()
    client.get_fundamentals("AAPL")
    client.get_fundamentals("AAPL")

    assert counter["fetches"] == 2  # no caching
