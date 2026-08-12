"""
Tests for PeerComparisonAgent metric extraction - per-peer period disclosure.
All synthetic - _extract_metrics is a pure transform of a yfinance info dict.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.peer_agent import PeerComparisonAgent


def test_extract_metrics_surfaces_period_end_when_available():
    """Each peer row must carry its own TTM cutoff (mostRecentQuarter) so
    peers on different fiscal calendars aren't presented as if their 'TTM'
    figures were all as of the same date."""
    info = {
        "shortName": "Test Co",
        "trailingPE": 20.0,
        "revenueGrowth": 0.1,
        "profitMargins": 0.2,
        "returnOnEquity": 0.15,
        "debtToEquity": 50.0,
        "mostRecentQuarter": 1_780_000_000,  # epoch seconds
    }
    row = PeerComparisonAgent._extract_metrics("TST", info)
    assert "period_end" in row
    assert row["period_end"] is not None
    # ISO YYYY-MM-DD
    assert len(row["period_end"]) == 10 and row["period_end"][4] == "-"


def test_extract_metrics_period_end_none_when_missing():
    """A company for which yfinance doesn't report mostRecentQuarter still
    produces a row - period_end is None rather than raising."""
    row = PeerComparisonAgent._extract_metrics("TST", {"shortName": "X"})
    assert row["period_end"] is None
