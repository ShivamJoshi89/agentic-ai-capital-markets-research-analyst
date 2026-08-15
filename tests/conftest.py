"""Shared pytest fixtures."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_sources.yfinance_client import YFinanceClient


@pytest.fixture(autouse=True)
def _clear_yfinance_cache():
    """The yfinance result cache is class-level and shared across instances;
    clear it around every test so one test's monkeypatched ticker data can't
    leak into another through the cache."""
    YFinanceClient._cache.clear()
    yield
    YFinanceClient._cache.clear()
