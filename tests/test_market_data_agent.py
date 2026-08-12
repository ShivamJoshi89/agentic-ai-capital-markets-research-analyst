"""
Tests for MarketDataAgent._calculate_metrics - calendar-YTD vs trailing-12mo
and the insufficient-price-history guard. All synthetic, no network access.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.market_data_agent import MarketDataAgent


def make_history(start, end, start_price=100.0, end_price=200.0):
    """A business-day OHLC-ish history with a linear Close ramp and constant
    volume - enough for _calculate_metrics, which only reads Close/Volume."""
    idx = pd.bdate_range(start, end)
    close = np.linspace(start_price, end_price, len(idx))
    return pd.DataFrame({"Close": close, "Volume": np.full(len(idx), 1_000_000)}, index=idx)


def test_ytd_return_is_calendar_year_not_trailing_twelve_months():
    """The headline 'ytd_return' must be measured from the first trading bar
    of the latest bar's calendar year, not from history.iloc[0] (~12 months
    back against a rolling 1y fetch). On a series spanning a year boundary
    these differ materially, so a coincidental match can't hide the bug."""
    hist = make_history("2025-08-11", "2026-08-07", 100.0, 200.0)
    metrics = MarketDataAgent()._calculate_metrics(hist)

    latest = hist["Close"].iloc[-1]
    ytd_rows = hist[hist.index.year == hist.index[-1].year]
    expected_ytd = round((latest / ytd_rows["Close"].iloc[0] - 1) * 100, 2)
    trailing_1y = round((latest / hist["Close"].iloc[0] - 1) * 100, 2)

    assert metrics["ytd_basis"] == "calendar_ytd"
    assert metrics["ytd_return"] == expected_ytd
    # The bug's answer (trailing-12mo) must be meaningfully different, so this
    # test genuinely distinguishes the two rather than passing by accident.
    assert abs(metrics["ytd_return"] - trailing_1y) > 10


def test_ytd_falls_back_to_trailing_when_no_calendar_year_base_yet():
    """Early January: fewer than two bars in the current calendar year. YTD
    can't be computed, so it falls back to the full trailing series and says
    so via ytd_basis (so no consumer mislabels it as calendar-YTD)."""
    # Series ends 2026-01-01 with only that single 2026 bar.
    hist = make_history("2025-02-03", "2026-01-01", 100.0, 150.0)
    metrics = MarketDataAgent()._calculate_metrics(hist)
    assert metrics["ytd_basis"] == "trailing_since_series_start"
    assert metrics["ytd_return"] is not None


def test_windowed_returns_none_when_history_too_short():
    """A short history (recent IPO) must return None for any window longer
    than the available history, rather than silently borrowing iloc[0] under
    every window's label (which made 3M and 6M collapse to the same number)."""
    hist = make_history("2026-01-02", "2026-02-13")  # ~30 business days
    assert len(hist) < 63
    metrics = MarketDataAgent()._calculate_metrics(hist)

    assert metrics["one_month_return"] is not None  # 21 <= len, computable
    assert metrics["three_month_return"] is None     # 63 > len
    assert metrics["six_month_return"] is None        # 126 > len


def test_recent_ipo_in_early_january_combines_both_guards():
    """Combined 1a + 1b edge case (not just each in isolation): a recent IPO
    (~35 trading days of history) analyzed in early January must simultaneously
    (a) fall back to trailing YTD - no calendar-year base bar exists yet - AND
    (b) return None for the 3M/6M windows that exceed its short history, while
    the 1M window (which fits) still computes."""
    hist = make_history("2025-11-14", "2026-01-01", 50.0, 60.0)
    assert len(hist) < 63  # too short for the 3M/6M windows
    assert sum(d.year == 2026 for d in hist.index) < 2  # early January: no YTD base

    metrics = MarketDataAgent()._calculate_metrics(hist)
    # 1a fallback
    assert metrics["ytd_basis"] == "trailing_since_series_start"
    assert metrics["ytd_return"] is not None
    # 1b guard
    assert metrics["one_month_return"] is not None
    assert metrics["three_month_return"] is None
    assert metrics["six_month_return"] is None


def test_windowed_returns_all_present_with_full_history():
    """A full year of history yields all three windowed returns, and 3M and
    6M are genuinely different (the borrowed-iloc[0] bug made them equal)."""
    hist = make_history("2025-08-11", "2026-08-07", 100.0, 200.0)
    metrics = MarketDataAgent()._calculate_metrics(hist)
    assert metrics["one_month_return"] is not None
    assert metrics["three_month_return"] is not None
    assert metrics["six_month_return"] is not None
    assert metrics["three_month_return"] != metrics["six_month_return"]
