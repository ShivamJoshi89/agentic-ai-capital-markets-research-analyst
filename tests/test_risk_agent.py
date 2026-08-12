"""
Tests for RiskAgent sector-aware valuation gating (REIT P/E suppression).
All synthetic - no network access required.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.risk_agent import RiskAgent


def make_fundamentals(sector, pe_ratio):
    """Minimal formatted-fundamentals dict as _format_fundamentals would
    produce, carrying just the fields the valuation risk check reads."""
    return {
        "pe_ratio": f"{pe_ratio:.2f}",
        "pb_ratio": "1.40",
        "profit_margin": "20.00%",
        "debt_to_equity": "0.50x",
        "is_reit": sector == "Real Estate",
        "is_financial_sector": sector == "Financial Services",
    }


def risk_titles(sector, pe_ratio):
    analysis = {
        "market_data": {},
        "fundamentals_data": {"ticker": "X", "success": True, "fundamentals": make_fundamentals(sector, pe_ratio)},
        "news_data": {},
        "company_info": {"sector": sector, "company_name": "Test Co"},
        "macro_data": {},
        "financing_data": {},
    }
    return [r["title"] for r in RiskAgent().run("X", analysis)["risks"]]


def test_reit_pe_premium_valuation_flag_suppressed():
    """A REIT's GAAP P/E is structurally inflated by real-estate depreciation,
    so the generic >20x 'Premium Valuation Multiple' flag must not fire - it
    would trip on nearly every REIT as a GAAP artifact, not a real signal."""
    titles = risk_titles("Real Estate", pe_ratio=45.0)
    assert "Premium Valuation Multiple" not in titles


def test_non_reit_pe_premium_valuation_flag_still_fires():
    """The suppression must be REIT-specific: a normal company at the same
    45x P/E still gets flagged."""
    titles = risk_titles("Technology", pe_ratio=45.0)
    assert "Premium Valuation Multiple" in titles


def test_reit_below_threshold_unaffected():
    """Sanity: a REIT below the 20x threshold wouldn't have been flagged
    anyway - the suppression doesn't invent or remove anything at low P/E."""
    titles = risk_titles("Real Estate", pe_ratio=12.0)
    assert "Premium Valuation Multiple" not in titles


# ---------------------------------------------------------------------
# 4b - profit-margin severity scales with magnitude
# ---------------------------------------------------------------------

def profitability_flag(profit_margin_pct):
    fund = {
        "pe_ratio": "10.00",
        "profit_margin": f"{profit_margin_pct:.1f}%",
        "is_reit": False,
        "is_financial_sector": False,
    }
    analysis = {
        "market_data": {},
        "fundamentals_data": {"ticker": "X", "success": True, "fundamentals": fund},
        "news_data": {},
        "company_info": {"sector": "Technology", "company_name": "Test Co"},
        "macro_data": {},
        "financing_data": {},
    }
    risks = RiskAgent().run("X", analysis)["risks"]
    return next((r for r in risks if r["category"] == "Profitability"), None)


def test_thin_margin_is_medium():
    flag = profitability_flag(-5.0)
    assert flag is not None
    assert flag["title"] == "Thin Profit Margins"
    assert flag["severity"] == "Medium"


def test_large_operating_loss_escalates_to_high():
    """A margin below -25% must escalate to a distinct High-severity flag,
    not stay in the same Medium 'Thin Profit Margins' bucket as a -5% margin."""
    for pm in (-50.0, -150.0):
        flag = profitability_flag(pm)
        assert flag is not None, pm
        assert flag["title"] == "Substantial Operating Losses", pm
        assert flag["severity"] == "High", pm


def test_margin_severity_is_not_flat_across_magnitudes():
    """The whole point: severity/title must differ between a -5% and a -150%
    margin rather than being one flat bucket for everything under 5%."""
    thin = profitability_flag(-5.0)
    severe = profitability_flag(-150.0)
    assert (thin["title"], thin["severity"]) != (severe["title"], severe["severity"])


# ---------------------------------------------------------------------
# Downstream consequence of the profit_margin fix (real corrected magnitudes):
# a company whose margin Yahoo reported wrong must now flag correctly. These
# lock in the live-confirmed before/after, not just the input value.
# ---------------------------------------------------------------------

def test_sony_corrected_margin_produces_no_thin_flag():
    """SONY's real net margin is ~+8.8% (Yahoo wrongly reported -1.7%). At the
    corrected value it must NOT trip 'Thin Profit Margins' - confirmed live
    that the false Medium flag disappears after the profit_margin fix."""
    assert profitability_flag(8.77) is None


def test_atalf_corrected_margin_escalates_to_substantial_losses():
    """ATALF's real margin is deeply negative (~-120,130%; Yahoo reported 0.0,
    which understated it to a mere 'Thin Profit Margins' Medium). At the
    corrected value it must escalate to the High 'Substantial Operating
    Losses' flag."""
    flag = profitability_flag(-120130.47)
    assert flag is not None
    assert flag["title"] == "Substantial Operating Losses"
    assert flag["severity"] == "High"
