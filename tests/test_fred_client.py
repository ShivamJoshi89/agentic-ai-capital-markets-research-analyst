"""
Tests for FREDClient's FX conversion helper. All synthetic - no network
access required (the live `Fred` client is monkeypatched with a fake
that returns controlled pandas Series).
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_sources.fred_client import FREDClient


class FakeFred:
    """Stand-in for fredapi.Fred - returns a canned Series per series ID."""

    def __init__(self, series_by_id):
        self.series_by_id = series_by_id

    def get_series(self, series_id):
        return self.series_by_id[series_id]


def make_client(series_by_id):
    client = FREDClient.__new__(FREDClient)  # skip __init__ (no live Fred/API key needed)
    client.name = "FRED Client"
    client.fred = FakeFred(series_by_id)
    return client


def test_get_fx_rate_to_usd_inverts_foreign_per_usd_series():
    """JPY is quoted as yen-per-USD (DEXJPUS) - must invert to get USD-per-JPY."""
    series = pd.Series([159.16], index=pd.to_datetime(["2026-07-31"]))
    client = make_client({"DEXJPUS": series})

    result = client.get_fx_rate_to_usd("JPY")

    assert result["rate"] == 1 / 159.16
    assert result["as_of"] == "2026-07-31"


def test_get_fx_rate_to_usd_uses_usd_per_unit_series_directly():
    """EUR is quoted as USD-per-EUR (DEXUSEU) - used directly, no inversion."""
    series = pd.Series([1.1519], index=pd.to_datetime(["2026-07-31"]))
    client = make_client({"DEXUSEU": series})

    result = client.get_fx_rate_to_usd("EUR")

    assert result["rate"] == 1.1519


def test_get_fx_rate_to_usd_converts_a_real_figure_to_a_sane_usd_value():
    """End-to-end sanity: Toyota's real JPY revenue, converted, should land
    in Toyota's real-world USD revenue ballpark (hundreds of billions)."""
    series = pd.Series([159.16], index=pd.to_datetime(["2026-07-31"]))
    client = make_client({"DEXJPUS": series})

    fx = client.get_fx_rate_to_usd("JPY")
    revenue_jpy = 51_957_024_686_080
    revenue_usd = revenue_jpy * fx["rate"]

    assert 250_000_000_000 < revenue_usd < 400_000_000_000


def test_get_fx_rate_to_usd_returns_none_for_usd():
    client = make_client({})
    assert client.get_fx_rate_to_usd("USD") is None


def test_get_fx_rate_to_usd_returns_none_for_unmapped_currency():
    # TRY (Turkish Lira) is deliberately NOT in FX_SERIES_MAP - an unmapped
    # currency must return None rather than risk a wrong/unverified series.
    client = make_client({})
    assert client.get_fx_rate_to_usd("TRY") is None


def test_get_fx_rate_to_usd_inverts_added_adr_currencies():
    """Currencies added after the 100-ticker sweep (INR/BRL/CNY/KRW...) are
    quoted foreign-per-USD and must invert. Guards against a future edit
    flipping one to the wrong direction (which would mis-scale by rate^2)."""
    for currency, series_id, raw in [("INR", "DEXINUS", 95.21), ("BRL", "DEXBZUS", 5.0882),
                                     ("CNY", "DEXCHUS", 6.7474), ("KRW", "DEXKOUS", 1409.94)]:
        series = pd.Series([raw], index=pd.to_datetime(["2026-08-07"]))
        client = make_client({series_id: series})
        result = client.get_fx_rate_to_usd(currency)
        assert result["rate"] == 1 / raw, currency


def test_get_fx_rate_to_usd_aud_used_directly():
    """AUD (DEXUSAL) is quoted USD-per-AUD - used directly, not inverted."""
    series = pd.Series([0.7064], index=pd.to_datetime(["2026-08-07"]))
    client = make_client({"DEXUSAL": series})
    assert client.get_fx_rate_to_usd("AUD")["rate"] == 0.7064


def test_added_currency_converts_real_figure_to_sane_usd():
    """End-to-end sanity for an added currency: HDFC Bank's real INR revenue,
    converted, should land in its real-world USD ballpark (~$30B)."""
    series = pd.Series([95.21], index=pd.to_datetime(["2026-08-07"]))
    client = make_client({"DEXINUS": series})
    fx = client.get_fx_rate_to_usd("INR")
    revenue_usd = 2_950_000_000_000 * fx["rate"]  # ~2.95T INR
    assert 25_000_000_000 < revenue_usd < 40_000_000_000


def test_get_fx_rate_to_usd_returns_none_when_fred_unavailable():
    client = FREDClient.__new__(FREDClient)
    client.name = "FRED Client"
    client.fred = None  # matches __init__'s behavior with no API key/library
    assert client.get_fx_rate_to_usd("JPY") is None


def test_get_fx_rate_to_usd_returns_none_on_empty_series():
    client = make_client({"DEXJPUS": pd.Series([], dtype=float)})
    assert client.get_fx_rate_to_usd("JPY") is None
