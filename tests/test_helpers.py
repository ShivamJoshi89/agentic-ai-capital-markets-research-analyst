"""
Tests for validate_ticker - the single input-validation gate before any
external call. Locks in that it accepts the real hyphenated securities the
100-ticker sweep (seed 20260811) confirmed the pipeline handles, while still
rejecting malformed/injection input.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.helpers import validate_ticker

# The exact hyphenated tickers drawn in the sweep and confirmed handled.
SWEEP_HYPHENATED = ["BEP-PA", "BKSY-WT", "GSL-PB", "LZM-WT", "MAA-PI", "OPP-PA", "TRTN-PG", "VII-UN"]
CURATED = ["AAPL", "JPM", "MSFT", "NVDA", "O", "PGR", "DPZ", "MRNA", "TM", "SONY", "NVO"]
CLASS_SHARES = ["BRK-B", "BF-B"]
MALFORMED = ["123XYZ", "AAP L", "'; DROP", "", "AAPL;", "AAAA-BBB", "-PA", "AAPL-", "a b c", "AAPL.B"]


@pytest.mark.parametrize("ticker", SWEEP_HYPHENATED)
def test_hyphenated_sweep_tickers_accepted(ticker):
    """Regression: these were rejected by the old ^[A-Z]{1,5}$ despite the
    sweep confirming the pipeline handled them gracefully."""
    assert validate_ticker(ticker) is True


@pytest.mark.parametrize("ticker", CURATED + CLASS_SHARES)
def test_plain_and_class_share_tickers_accepted(ticker):
    assert validate_ticker(ticker) is True


@pytest.mark.parametrize("ticker", MALFORMED)
def test_malformed_and_injection_rejected(ticker):
    """The guard still does its job: digits, spaces, quotes/semicolons, empty,
    over-long suffixes, dangling hyphens, and dotted forms are rejected."""
    assert validate_ticker(ticker) is False
