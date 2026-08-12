"""
Tests for the Financing & Dilution Risk Agent and the SEC EDGAR filing
classifier. All synthetic - no network access required.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.financing_risk_agent import FinancingRiskAgent
from data_sources.sec_edgar_client import classify_financing_filing


# ---------------------------------------------------------------------
# classify_financing_filing
# ---------------------------------------------------------------------

def test_classify_shelf_registration():
    assert classify_financing_filing("S-3") is not None


def test_classify_prospectus_supplement():
    assert classify_financing_filing("424B5") is not None


def test_classify_8k_with_financing_item():
    reason = classify_financing_filing("8-K", "1.01,5.02")
    assert reason is not None
    assert "1.01" in reason


def test_classify_8k_without_financing_item():
    assert classify_financing_filing("8-K", "5.02,2.02") is None


def test_classify_unrelated_form():
    assert classify_financing_filing("10-Q") is None


def test_classify_effect_not_counted_as_financing():
    """EFFECT (notice of effectiveness) applies to any registration - including
    routine S-8 employee stock plans - and, when it corresponds to a real
    S-1/S-3, double-counts an event already captured by that form. It must not
    be classified as a financing filing on its own."""
    assert classify_financing_filing("EFFECT") is None


def test_classify_substantive_registration_forms_still_counted():
    """Dropping EFFECT must not affect the substantive capital-raising forms."""
    assert classify_financing_filing("S-1") is not None
    assert classify_financing_filing("S-3") is not None
    assert classify_financing_filing("424B5") is not None


def test_get_financing_filings_excludes_effect(monkeypatch):
    """Integration: an EFFECT filing in the lookback window (with no S-1/S-3
    of its own) is not counted, while a real S-3 in the same window is."""
    agent = make_agent()
    recent = [
        {"form": "EFFECT", "filing_date": "2026-07-01", "accession_number": "1", "items": "", "url": ""},
        {"form": "S-3", "filing_date": "2026-06-01", "accession_number": "2", "items": "", "url": ""},
        {"form": "10-Q", "filing_date": "2026-05-01", "accession_number": "3", "items": "", "url": ""},
    ]
    monkeypatch.setattr(agent.edgar, "get_recent_filings", lambda cik, limit=200: recent)
    result = agent.edgar.get_financing_filings("fakecik")
    forms = [f["form"] for f in result]
    assert "EFFECT" not in forms
    assert "S-3" in forms


def test_classify_8k_no_items():
    assert classify_financing_filing("8-K", "") is None


# ---------------------------------------------------------------------
# FinancingRiskAgent - pure calculation helpers
# ---------------------------------------------------------------------

def make_agent():
    """FinancingRiskAgent.__init__ only opens a requests.Session - no
    network call happens until .run()/.edgar.* methods are invoked, so
    this is safe to call without mocking anything."""
    return FinancingRiskAgent()


def test_pct_change_basic():
    agent = make_agent()
    old = {"end": "2024-01-01", "shares": 100_000_000}
    new = {"end": "2025-01-01", "shares": 130_000_000}
    assert agent._pct_change(old, new) == 30.0


def test_pct_change_none_when_old_missing():
    agent = make_agent()
    new = {"end": "2025-01-01", "shares": 130_000_000}
    assert agent._pct_change(None, new) is None


def test_find_comparator_picks_closest_at_least_min_days_back():
    agent = make_agent()
    series = [
        {"end": "2023-06-30", "shares": 90_000_000},
        {"end": "2024-01-01", "shares": 100_000_000},
        {"end": "2024-07-01", "shares": 110_000_000},
        {"end": "2025-01-01", "shares": 130_000_000},
    ]
    latest = series[-1]
    year_ago = agent._find_comparator(series, latest, min_days=330)
    assert year_ago["end"] == "2024-01-01"

    quarter_ago = agent._find_comparator(series, latest, min_days=75)
    assert quarter_ago["end"] == "2024-07-01"


def test_analyze_runway_cash_flow_positive():
    agent = make_agent()
    fundamentals_data = {
        "fundamentals": {"cash": "50,000,000", "operating_cash_flow": "10,000,000"}
    }
    runway = agent._analyze_runway(fundamentals_data)
    assert runway["available"] is True
    assert runway["cash_flow_positive"] is True
    assert runway["runway_months"] is None


def test_analyze_runway_burning_cash():
    agent = make_agent()
    # $12M cash, burning $6M/year -> $0.5M/month -> 24 months runway
    fundamentals_data = {
        "fundamentals": {"cash": "12,000,000", "operating_cash_flow": "-6,000,000"}
    }
    runway = agent._analyze_runway(fundamentals_data)
    assert runway["available"] is True
    assert runway["cash_flow_positive"] is False
    assert runway["runway_months"] == 24.0


def test_analyze_runway_unavailable_when_missing_data():
    agent = make_agent()
    runway = agent._analyze_runway({"fundamentals": {"cash": "N/A", "operating_cash_flow": "N/A"}})
    assert runway["available"] is False


def test_overhang_level_high():
    agent = make_agent()
    dilution = {"available": True, "yoy_change_pct": 25}
    runway = {"cash_flow_positive": False, "runway_months": 4}
    filings = [{"form": "S-3"}, {"form": "424B5"}, {"form": "8-K"}]
    assert agent._overhang_level(dilution, runway, filings) == "High"


def test_overhang_level_low_when_clean():
    agent = make_agent()
    dilution = {"available": True, "yoy_change_pct": 1.2}
    runway = {"cash_flow_positive": True, "runway_months": None}
    filings = []
    assert agent._overhang_level(dilution, runway, filings) == "Low"


def test_build_flags_flags_rapid_dilution():
    agent = make_agent()
    dilution = {"available": True, "yoy_change_pct": 22.0}
    runway = {"available": False}
    flags = agent._build_flags(dilution, runway, [], None)
    titles = [f["title"] for f in flags]
    assert "Rapid Share Dilution" in titles
    assert flags[0]["category"] == "Financing"


def test_build_flags_empty_when_clean():
    agent = make_agent()
    dilution = {"available": True, "yoy_change_pct": 0.5}
    runway = {"available": True, "cash_flow_positive": True}
    flags = agent._build_flags(dilution, runway, [], None)
    assert flags == []


# ---------------------------------------------------------------------
# Cash-runway sector gate: negative OCF is structural (not a burn signal)
# for banks/insurers/REITs, so the runway flag and overhang score are
# suppressed for those sectors.
# ---------------------------------------------------------------------

# ~6 months runway: $30M cash, burning $60M/yr -> would be a High flag in a
# non-exempt sector.
_BURNING_RUNWAY = {"available": True, "cash_flow_positive": False, "runway_months": 6.0}
_CLEAN_DILUTION = {"available": True, "yoy_change_pct": 1.0}


def test_build_flags_runway_suppressed_for_financial_sector():
    agent = make_agent()
    bank_info = {"sector": "Financial Services", "company_name": "Big Bank NA"}
    flags = agent._build_flags(_CLEAN_DILUTION, _BURNING_RUNWAY, [], bank_info)
    assert "Limited Cash Runway" not in [f["title"] for f in flags]


def test_build_flags_runway_suppressed_for_real_estate_sector():
    agent = make_agent()
    reit_info = {"sector": "Real Estate", "company_name": "Some REIT"}
    flags = agent._build_flags(_CLEAN_DILUTION, _BURNING_RUNWAY, [], reit_info)
    assert "Limited Cash Runway" not in [f["title"] for f in flags]


def test_build_flags_runway_still_fires_for_non_exempt_sector():
    """The gate must be sector-specific, not a blanket suppression - a real
    operating company with a 6-month burn still gets the flag."""
    agent = make_agent()
    tech_info = {"sector": "Technology", "company_name": "Cash-Burning Startup"}
    flags = agent._build_flags(_CLEAN_DILUTION, _BURNING_RUNWAY, [], tech_info)
    runway_flag = next((f for f in flags if f["title"] == "Limited Cash Runway"), None)
    assert runway_flag is not None
    assert runway_flag["severity"] == "High"


def test_build_flags_runway_still_fires_when_sector_unknown():
    """No company_info (sector unknown) must not silently suppress the flag -
    absence of a sector is not evidence of an exempt sector."""
    agent = make_agent()
    flags = agent._build_flags(_CLEAN_DILUTION, _BURNING_RUNWAY, [], None)
    assert "Limited Cash Runway" in [f["title"] for f in flags]


def test_overhang_level_runway_not_scored_for_financial_sector():
    """A bank with a burn-based runway but nothing else must not be scored up
    to Medium off that structural-OCF runway alone."""
    agent = make_agent()
    bank_info = {"sector": "Financial Services"}
    assert agent._overhang_level(_CLEAN_DILUTION, _BURNING_RUNWAY, [], bank_info) == "Low"
    # Same inputs, non-exempt sector -> runway DOES contribute (score 1 -> Medium range needs 2;
    # pair with one filing to confirm the runway point is actually being counted for tech).
    tech_info = {"sector": "Technology"}
    assert agent._overhang_level(_CLEAN_DILUTION, _BURNING_RUNWAY, [{"form": "S-3"}], tech_info) == "Medium"


# ---------------------------------------------------------------------
# Balance-sheet growth vs contraction proxy: refines the runway exemption so
# a shrinking financial (potential stress) isn't waved off like a growing one
# (funding growth). Both have negative OCF; the total-assets YoY trend
# distinguishes them.
# ---------------------------------------------------------------------

def _runway_with_trend(total_assets_yoy):
    r = {"available": True, "cash_flow_positive": False, "runway_months": 6.0}
    if total_assets_yoy is not None:
        r["total_assets_yoy_change_pct"] = total_assets_yoy
    return r


def test_growing_bank_runway_still_suppressed():
    """Growing bank (assets up YoY) + negative OCF = funding growth -> stays
    suppressed, and does NOT get the contraction flag."""
    agent = make_agent()
    bank_info = {"sector": "Financial Services", "company_name": "Growing Bank"}
    flags = agent._build_flags(_CLEAN_DILUTION, _runway_with_trend(10.2), [], bank_info)
    titles = [f["title"] for f in flags]
    assert "Limited Cash Runway" not in titles
    assert "Balance Sheet Contraction" not in titles


def test_shrinking_bank_gets_distinct_contraction_flag():
    """Shrinking bank (assets down YoY) + negative OCF = the opposite pattern
    -> a distinct 'Balance Sheet Contraction' flag, NOT the burn-rate 'Limited
    Cash Runway' flag."""
    agent = make_agent()
    bank_info = {"sector": "Financial Services", "company_name": "Shrinking Bank"}
    flags = agent._build_flags(_CLEAN_DILUTION, _runway_with_trend(-8.0), [], bank_info)
    titles = [f["title"] for f in flags]
    assert "Balance Sheet Contraction" in titles
    assert "Limited Cash Runway" not in titles  # must NOT be framed as burn-rate insolvency
    contraction = next(f for f in flags if f["title"] == "Balance Sheet Contraction")
    assert "8.0%" in contraction["metric"]
    assert contraction["severity"] == "Medium"


def test_flat_bank_stays_suppressed():
    """Flat balance sheet (0% YoY) is treated as the growth/stable side, not
    contraction - a stable bank shouldn't be flagged as contracting."""
    agent = make_agent()
    bank_info = {"sector": "Financial Services", "company_name": "Flat Bank"}
    titles = [f["title"] for f in agent._build_flags(_CLEAN_DILUTION, _runway_with_trend(0.0), [], bank_info)]
    assert "Balance Sheet Contraction" not in titles
    assert "Limited Cash Runway" not in titles


def test_trend_unknown_falls_back_to_blanket_suppression():
    """When the asset-trend proxy isn't available, the code must fall back to
    the blanket suppression rather than inventing a contraction signal."""
    agent = make_agent()
    bank_info = {"sector": "Financial Services", "company_name": "No-Trend Bank"}
    titles = [f["title"] for f in agent._build_flags(_CLEAN_DILUTION, _runway_with_trend(None), [], bank_info)]
    assert "Balance Sheet Contraction" not in titles
    assert "Limited Cash Runway" not in titles


def test_shrinking_assets_in_non_exempt_sector_uses_burn_flag_not_contraction():
    """The contraction path is specific to balance-sheet-driven sectors: a
    normal operating company with a 6-month burn still gets the burn-rate
    runway flag regardless of its asset trend."""
    agent = make_agent()
    tech_info = {"sector": "Technology", "company_name": "Startup"}
    titles = [f["title"] for f in agent._build_flags(_CLEAN_DILUTION, _runway_with_trend(-8.0), [], tech_info)]
    assert "Limited Cash Runway" in titles
    assert "Balance Sheet Contraction" not in titles


def test_analyze_runway_marks_sector_exempt_from_fundamentals_flags():
    """sector_exempt must be derived on the runway dict so every downstream
    consumer (summary, LLM note, UI card) reads one source of truth."""
    agent = make_agent()
    bank = agent._analyze_runway({"fundamentals": {
        "cash": "30,000,000,000", "operating_cash_flow": "-60,000,000,000", "is_financial_sector": True}})
    assert bank["sector_exempt"] is True
    tech = agent._analyze_runway({"fundamentals": {
        "cash": "30,000,000,000", "operating_cash_flow": "-60,000,000,000", "is_financial_sector": False}})
    assert tech["sector_exempt"] is False


# ---------------------------------------------------------------------
# _summarize must not narrate a suppressed sector's negative OCF as a
# burn-rate runway (the residual-leak fix).
# ---------------------------------------------------------------------

def _summary_runway(sector_exempt, cash_flow_positive=False, ta_yoy=None, runway_months=6.0):
    return {"available": True, "cash_flow_positive": cash_flow_positive,
            "runway_months": runway_months, "sector_exempt": sector_exempt,
            "total_assets_yoy_change_pct": ta_yoy}


def test_summarize_does_not_frame_bank_as_burn_rate_runway():
    agent = make_agent()
    text = agent._summarize("Low", _CLEAN_DILUTION, _summary_runway(True, ta_yoy=10.2), [])
    assert "burn rate" not in text
    assert "cash runway is ~" not in text
    assert "not a meaningful measure" in text


def test_summarize_states_contraction_for_shrinking_bank():
    agent = make_agent()
    text = agent._summarize("Low", _CLEAN_DILUTION, _summary_runway(True, ta_yoy=-8.0), [])
    assert "burn rate" not in text
    assert "shrank 8.0%" in text


def test_summarize_still_uses_burn_rate_for_non_exempt():
    agent = make_agent()
    text = agent._summarize("Medium", _CLEAN_DILUTION, _summary_runway(False, ta_yoy=None), [])
    assert "burn rate" in text


def test_build_flags_flags_reverse_split():
    agent = make_agent()
    dilution = {
        "available": True, "yoy_change_pct": None,
        "likely_split": True, "split_direction": "reverse", "split_confidence": "confirmed",
    }
    runway = {"available": False}
    flags = agent._build_flags(dilution, runway, [], None)
    titles = [f["title"] for f in flags]
    assert "Reverse Split — Dilution Trend Obscured" in titles


def test_build_flags_flags_forward_split():
    agent = make_agent()
    dilution = {
        "available": True, "yoy_change_pct": 2.0,
        "likely_split": True, "split_direction": "forward", "split_confidence": "confirmed",
    }
    runway = {"available": False}
    flags = agent._build_flags(dilution, runway, [], None)
    titles = [f["title"] for f in flags]
    assert "Stock Split Detected — Share-Count Jump Is Not Dilution" in titles
    assert "Rapid Share Dilution" not in titles
    assert "Elevated Share Dilution" not in titles


def test_build_flags_forward_split_heuristic_notes_lower_confidence():
    agent = make_agent()
    dilution = {
        "available": True, "yoy_change_pct": 2.0,
        "likely_split": True, "split_direction": "forward", "split_confidence": "heuristic",
    }
    runway = {"available": False}
    flags = agent._build_flags(dilution, runway, [], None)
    split_flag = next(f for f in flags if f["title"] == "Stock Split Detected — Share-Count Jump Is Not Dilution")
    assert "lower-confidence" in split_flag["description"]


# ---------------------------------------------------------------------
# FinancingRiskAgent - split detection in _analyze_dilution
# ---------------------------------------------------------------------

def test_analyze_dilution_detects_reverse_split(monkeypatch):
    agent = make_agent()
    series = [
        {"end": "2024-01-01", "shares": 10_000_000},
        {"end": "2024-06-01", "shares": 12_000_000},
        {"end": "2025-01-01", "shares": 15_000_000},
        {"end": "2025-02-01", "shares": 500_000},  # reverse split: -96.7%
        {"end": "2025-05-01", "shares": 550_000},
        {"end": "2025-12-01", "shares": 600_000},
    ]
    monkeypatch.setattr(agent.edgar, "get_shares_outstanding_series", lambda cik: series)
    confirmed_splits = pd.Series([0.1], index=pd.to_datetime(["2025-02-05"]))
    monkeypatch.setattr(agent, "_get_split_events", lambda ticker: confirmed_splits)

    dilution = agent._analyze_dilution("fakecik", "FAKE")

    assert dilution["likely_split"] is True
    assert dilution["split_direction"] == "reverse"
    assert dilution["split_confidence"] == "confirmed"
    assert dilution["split_detected_at"] == "2025-02-01"
    # not enough post-split history yet for a valid YoY comparator
    assert dilution["yoy_change_pct"] is None
    # QoQ comparator (2025-05-01) is available post-split
    assert dilution["qoq_change_pct"] == pytest.approx(9.0909, abs=0.01)
    # raw pre-fix figure is preserved for transparency, not fed into flags/scoring
    assert dilution["raw_yoy_change_pct"] < -90


def test_analyze_dilution_no_false_positive_on_gradual_decline(monkeypatch):
    agent = make_agent()
    series = [
        {"end": "2024-01-01", "shares": 1_000_000_000},
        {"end": "2024-06-01", "shares": 980_000_000},
        {"end": "2025-01-01", "shares": 960_000_000},
        {"end": "2025-06-01", "shares": 945_000_000},
        {"end": "2025-12-01", "shares": 930_000_000},
    ]
    monkeypatch.setattr(agent.edgar, "get_shares_outstanding_series", lambda cik: series)

    dilution = agent._analyze_dilution("fakecik", "FAKE")

    assert dilution["likely_split"] is False
    assert "split_detected_at" not in dilution


def test_analyze_dilution_confirmed_forward_split_suppresses_dilution_reading(monkeypatch):
    """Fixture 1: a confirmed split in stock.splits + a large share-count
    jump -> neutral note, dilution reading recomputed post-split."""
    agent = make_agent()
    series = [
        {"end": "2025-03-31", "shares": 100_000_000},
        {"end": "2025-06-30", "shares": 100_500_000},
        {"end": "2025-09-30", "shares": 101_000_000},
        {"end": "2025-12-31", "shares": 101_200_000},
        {"end": "2026-06-30", "shares": 405_000_000},  # 4-for-1 forward split
    ]
    monkeypatch.setattr(agent.edgar, "get_shares_outstanding_series", lambda cik: series)
    confirmed_splits = pd.Series([4.0], index=pd.to_datetime(["2026-06-15"]))
    monkeypatch.setattr(agent, "_get_split_events", lambda ticker: confirmed_splits)

    dilution = agent._analyze_dilution("fakecik", "FAKE")

    assert dilution["likely_split"] is True
    assert dilution["split_direction"] == "forward"
    assert dilution["split_confidence"] == "confirmed"
    assert dilution["raw_yoy_change_pct"] == pytest.approx(302.985, abs=0.01)
    # no post-split comparator exists yet in this fixture (only one point
    # after the split) - the raw, misleading +303% reading must not be
    # what feeds the dilution flag/overhang score
    assert dilution["yoy_change_pct"] is None


def test_analyze_dilution_large_jump_without_confirming_split_still_flags_dilution(monkeypatch):
    """Fixture 2: a large jump of similar magnitude, but stock.splits (real,
    successfully-fetched data) has nothing near that date -> treated as
    genuine dilution, not masked as a split. This is the case a pure
    magnitude threshold would have gotten wrong."""
    agent = make_agent()
    series = [
        {"end": "2025-03-31", "shares": 100_000_000},
        {"end": "2025-06-30", "shares": 100_500_000},
        {"end": "2025-09-30", "shares": 101_000_000},
        {"end": "2025-12-31", "shares": 101_200_000},
        {"end": "2026-06-30", "shares": 405_000_000},  # large raise, not a split
    ]
    monkeypatch.setattr(agent.edgar, "get_shares_outstanding_series", lambda cik: series)
    # Real split data exists for this ticker (e.g. a split years ago) but
    # nothing anywhere near the 2026-06-30 jump.
    unrelated_splits = pd.Series([2.0], index=pd.to_datetime(["2015-01-01"]))
    monkeypatch.setattr(agent, "_get_split_events", lambda ticker: unrelated_splits)

    dilution = agent._analyze_dilution("fakecik", "FAKE")

    assert dilution["likely_split"] is False
    assert "split_detected_at" not in dilution
    # the raw (large, genuine) dilution reading stands
    assert dilution["yoy_change_pct"] == pytest.approx(302.985, abs=0.01)


def test_analyze_dilution_split_data_unavailable_falls_back_to_heuristic(monkeypatch):
    """Fixture 3: stock.splits unavailable (fetch failed) + large jump ->
    falls back to the magnitude heuristic, marked lower-confidence."""
    agent = make_agent()
    series = [
        {"end": "2025-03-31", "shares": 100_000_000},
        {"end": "2025-06-30", "shares": 100_500_000},
        {"end": "2025-09-30", "shares": 101_000_000},
        {"end": "2025-12-31", "shares": 101_200_000},
        {"end": "2026-06-30", "shares": 405_000_000},
    ]
    monkeypatch.setattr(agent.edgar, "get_shares_outstanding_series", lambda cik: series)
    monkeypatch.setattr(agent, "_get_split_events", lambda ticker: None)

    dilution = agent._analyze_dilution("fakecik", "FAKE")

    assert dilution["likely_split"] is True
    assert dilution["split_direction"] == "forward"
    assert dilution["split_confidence"] == "heuristic"
