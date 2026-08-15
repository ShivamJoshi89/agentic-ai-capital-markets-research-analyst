"""
Tests for equity-derived ratio sourcing (roe/roa/debt_to_equity/pb_ratio)
and the negative-equity handling in FinancialsAgent and RiskAgent.
All synthetic - no network access required.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.fundamentals_agent import FinancialsAgent
from agents.risk_agent import RiskAgent
from data_sources.yfinance_client import YFinanceClient


# ---------------------------------------------------------------------
# YFinanceClient._average_of_latest_two_periods
# ---------------------------------------------------------------------

def make_statement(row_name, values, dates=None):
    """A minimal statement DataFrame shaped like yfinance's balance_sheet/
    quarterly_balance_sheet: rows are line items, columns are real
    Timestamps (most-recent first) - matching real yfinance data shape,
    which the date-gap tolerance check depends on being able to subtract.
    Defaults to standard ~91-day-spaced quarterly dates if none are given;
    pass explicit `dates` to simulate irregular/stub reporting periods."""
    if dates is None:
        end = pd.Timestamp("2026-06-30")
        dates = pd.DatetimeIndex([end - pd.DateOffset(days=91 * i) for i in range(len(values))])
    else:
        dates = pd.to_datetime(dates)
    return pd.DataFrame({row_name: values}, index=dates).T


def test_average_of_latest_two_periods_uses_year_ago_quarter_not_adjacent_quarter():
    """The standard ROE/ROA basis averages equity at the start and end of
    the TTM window the net income was earned over - i.e. this quarter (Q0)
    and the quarter ~12 months prior (Q-4), not the immediately preceding
    quarter (Q-1). Q-1 is given a distinct value from both Q0 and Q-4 so an
    adjacent-quarter bug would produce a detectably different (and wrong)
    result rather than silently passing. Dates are exactly 365/274/183/91
    days back, matching the real ~91-day quarterly cadence verified live
    for AAPL/JPM/MSFT/TM/SONY/NVO."""
    quarterly = make_statement(
        "Stockholders Equity",
        [107_520_000_000, 106_491_000_000, 88_190_000_000, 73_733_000_000, 65_830_000_000],
        #  Q0                Q-1               Q-2              Q-3              Q-4
        dates=["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"],
    )
    result, basis, row = YFinanceClient._average_of_latest_two_periods(
        quarterly, None, ["Stockholders Equity"], fallback_value=999
    )
    assert basis == "year_ago_average"
    assert row == "Stockholders Equity"
    assert result == (107_520_000_000 + 65_830_000_000) / 2
    assert result != (107_520_000_000 + 106_491_000_000) / 2  # the adjacent-quarter bug's answer


def test_average_of_latest_two_periods_irregular_gap_falls_back_to_point_in_time():
    """A stub/irregular period (e.g. around an M&A or fiscal-year change)
    can make the 4-columns-back period NOT actually ~12 months prior, even
    though it's still 4 columns back. The tolerance check must catch this
    by date, not assume column position implies ~365 days."""
    quarterly = make_statement(
        "Stockholders Equity",
        [107_520_000_000, 106_491_000_000, 88_190_000_000, 73_733_000_000, 65_830_000_000],
        # Q-4 is only 200 days before Q0 - a stub period, not a real year-ago quarter
        dates=["2026-06-30", "2026-04-01", "2026-01-01", "2025-10-15", "2025-12-13"],
    )
    result, basis, row = YFinanceClient._average_of_latest_two_periods(
        quarterly, None, ["Stockholders Equity"], fallback_value=999
    )
    assert basis == "point_in_time_fallback"
    assert row == "Stockholders Equity"
    assert result == 107_520_000_000  # Q0 alone, not an average with the bogus Q-4


def test_average_of_latest_two_periods_insufficient_history_uses_point_in_time():
    """Fewer than 5 quarters (e.g. a recent IPO) means no genuine year-ago
    quarter exists yet - must fall back to the single latest value, not
    average two adjacent quarters (that would just reintroduce the bug)."""
    quarterly = make_statement("Stockholders Equity", [50_000_000, 45_000_000, 40_000_000])
    result, basis, row = YFinanceClient._average_of_latest_two_periods(
        quarterly, None, ["Stockholders Equity"], fallback_value=999
    )
    assert basis == "point_in_time_fallback"
    assert row == "Stockholders Equity"
    assert result == 50_000_000


def test_average_of_latest_two_periods_single_period_uses_that_value():
    quarterly = make_statement("Stockholders Equity", [50_000_000])
    result, basis, row = YFinanceClient._average_of_latest_two_periods(
        quarterly, None, ["Stockholders Equity"], fallback_value=999
    )
    assert basis == "point_in_time_fallback"
    assert row == "Stockholders Equity"
    assert result == 50_000_000


def test_average_of_latest_two_periods_falls_back_to_annual_then_point_in_time():
    # quarterly has the row but no data; annual has two periods, 1 year
    # apart - annual columns are already ~1 year apart, so (unlike
    # quarterly) adjacent annual columns are the correct year-ago pairing.
    quarterly = make_statement("Other Row", [1, 2])
    annual = make_statement("Stockholders Equity", [80_000_000, 70_000_000], dates=["2026-06-30", "2025-06-30"])
    result, basis, row = YFinanceClient._average_of_latest_two_periods(
        quarterly, annual, ["Stockholders Equity"], fallback_value=999
    )
    assert basis == "year_ago_average"
    assert row == "Stockholders Equity"
    assert result == (80_000_000 + 70_000_000) / 2

    # neither statement has the row at all -> point-in-time fallback
    result_none, basis_none, row_none = YFinanceClient._average_of_latest_two_periods(
        None, None, ["Stockholders Equity"], fallback_value=999
    )
    assert basis_none == "unavailable_fallback"
    assert row_none is None
    assert result_none == 999


# ---------------------------------------------------------------------
# YFinanceClient._yoy_change_pct - balance-sheet growth/contraction proxy
# ---------------------------------------------------------------------

def test_yoy_change_pct_uses_year_ago_period():
    """Percent change is current vs the period ~12 months prior (Q0 vs Q-4),
    not the adjacent quarter - same year-ago pairing as the averaging helper."""
    quarterly = make_statement(
        "Total Assets",
        [110_000_000_000, 108_000_000_000, 105_000_000_000, 102_000_000_000, 100_000_000_000],
        dates=["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"],
    )
    result = YFinanceClient._yoy_change_pct(quarterly, None, ["Total Assets"])
    assert result == pytest.approx((110_000_000_000 - 100_000_000_000) / 100_000_000_000 * 100)  # +10%


def test_yoy_change_pct_negative_for_shrinking_balance_sheet():
    quarterly = make_statement(
        "Total Assets",
        [92_000_000_000, 95_000_000_000, 98_000_000_000, 99_000_000_000, 100_000_000_000],
        dates=["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"],
    )
    result = YFinanceClient._yoy_change_pct(quarterly, None, ["Total Assets"])
    assert result == pytest.approx(-8.0)  # (92-100)/100


def test_yoy_change_pct_none_when_irregular_gap():
    """A stub/irregular period (4 columns back but not ~12 months) must return
    None (trend unknown), not a bogus change from a non-year-ago period."""
    quarterly = make_statement(
        "Total Assets",
        [110_000_000_000, 108_000_000_000, 105_000_000_000, 102_000_000_000, 100_000_000_000],
        dates=["2026-06-30", "2026-04-01", "2026-01-01", "2025-10-15", "2025-12-13"],
    )
    assert YFinanceClient._yoy_change_pct(quarterly, None, ["Total Assets"]) is None


def test_yoy_change_pct_none_when_insufficient_history():
    quarterly = make_statement("Total Assets", [100_000_000_000, 99_000_000_000, 98_000_000_000])
    assert YFinanceClient._yoy_change_pct(quarterly, None, ["Total Assets"]) is None


# ---------------------------------------------------------------------
# YFinanceClient._compute_equity_ratios - pure formula checks
# ---------------------------------------------------------------------

def test_compute_equity_ratios_roe_roa_use_average_not_point_in_time():
    """roe/roa must use average_equity/average_assets, while
    debt_to_equity/pb_ratio must use the point-in-time total_equity - the
    two are deliberately different values here so the test can't pass by
    accident if the code used the wrong one for either."""
    net_income = 100_000_000
    total_equity = 500_000_000      # point-in-time (current quarter)
    average_equity = 460_000_000    # average of current + prior quarter
    total_assets = 2_000_000_000
    average_assets = 1_900_000_000
    total_debt = 400_000_000
    market_cap = 5_000_000_000

    ratios = YFinanceClient._compute_equity_ratios(
        net_income=net_income, total_equity=total_equity, total_debt=total_debt,
        market_cap=market_cap, average_equity=average_equity, average_assets=average_assets,
    )

    # Point-in-time based
    assert ratios["debt_to_equity"] == round(total_debt / total_equity * 100, 2)
    assert ratios["pb_ratio"] == round(market_cap / total_equity, 2)
    # Average based
    assert ratios["roe"] == round(net_income / average_equity, 4)
    assert ratios["roa"] == round(net_income / average_assets, 4)
    # Sanity: confirm these actually differ from the point-in-time figures,
    # so the assertions above are meaningful rather than coincidental
    assert ratios["roe"] != round(net_income / total_equity, 4)
    assert ratios["roa"] != round(net_income / total_assets, 4)


def test_compute_equity_ratios_negative_equity_one_shared_value():
    """D/E and ROE/P/B must all be derived from the SAME total_equity.
    This test picks one negative equity value, independently derives the
    expected D/E from it, and asserts ROE/P/B are suppressed (None) rather
    than silently computed from a different (e.g. .info-sourced) equity
    figure that would disagree with debt_to_equity's sign/magnitude.
    """
    net_income = 50_000_000  # profitable, despite negative book equity
    total_equity = -200_000_000  # the one shared point-in-time equity value
    average_equity = -180_000_000  # also negative - averaging doesn't fix this
    total_debt = 300_000_000
    market_cap = 3_000_000_000

    ratios = YFinanceClient._compute_equity_ratios(
        net_income=net_income, total_equity=total_equity, total_debt=total_debt,
        market_cap=market_cap, average_equity=average_equity, average_assets=800_000_000,
    )

    expected_de = round(total_debt / total_equity * 100, 2)
    assert ratios["debt_to_equity"] == expected_de
    assert expected_de < 0  # negative equity -> negative D/E, not a small positive one

    # ROE/P/B must not be silently computed against a different (positive)
    # equity source - they're undefined here and must be None, not a
    # backwards-signed number implying a loss that didn't happen.
    assert ratios["roe"] is None
    assert ratios["pb_ratio"] is None

    # ROA is unaffected by equity sign (denominator is average_assets)
    assert ratios["roa"] == round(net_income / 800_000_000, 4)


def test_compute_equity_ratios_currency_mismatch_falls_back_to_info_price_to_book():
    """Foreign private issuer: financial statements in JPY, market_cap/price
    in USD (mirrors Toyota). market_cap / total_equity would be off by the
    FX rate (~150x for JPY) if computed directly - must fall back to
    yfinance's own FX-normalized priceToBook instead."""
    ratios = YFinanceClient._compute_equity_ratios(
        net_income=3_000_000_000_000,       # JPY
        total_equity=37_000_000_000_000,    # JPY
        total_debt=44_000_000_000_000,      # JPY
        market_cap=220_000_000_000,         # USD
        average_equity=37_000_000_000_000,
        average_assets=90_000_000_000_000,
        financial_currency="JPY",
        quote_currency="USD",
        info_price_to_book=15.42,
    )
    assert ratios["pb_ratio"] == 15.42
    # Falling back to .info is NOT presented with the same confidence as a
    # direct computation - Yahoo's own priceToBook has independently been
    # observed wrong for at least one real ADR (Toyota), so this basis
    # must be labeled explicitly rather than looking identical to "computed".
    assert ratios["pb_ratio_basis"] == "info_fallback_unverified"
    # debt_to_equity/roa/roe are same-currency (JPY/JPY) and unaffected
    assert ratios["debt_to_equity"] == round(44_000_000_000_000 / 37_000_000_000_000 * 100, 2)
    assert ratios["roe"] == round(3_000_000_000_000 / 37_000_000_000_000, 4)


def test_compute_equity_ratios_currency_mismatch_negative_equity_still_na():
    """Currency mismatch AND negative equity: negative-equity N/A must win,
    not the currency fallback (don't resurrect a signed P/B via .info)."""
    ratios = YFinanceClient._compute_equity_ratios(
        net_income=1_000_000_000,
        total_equity=-5_000_000_000,
        total_debt=15_000_000_000,
        market_cap=50_000_000_000,
        average_equity=-4_500_000_000,
        average_assets=20_000_000_000,
        financial_currency="JPY",
        quote_currency="USD",
        info_price_to_book=-3.1,
    )
    assert ratios["pb_ratio"] is None


def test_compute_equity_ratios_missing_market_cap_falls_back_to_info_price_to_book():
    """Same-currency case, but `.info` is missing marketCap for this call
    (a real, observed yfinance data gap, e.g. for O/Realty Income) - must
    still surface Yahoo's own priceToBook rather than losing it to N/A."""
    ratios = YFinanceClient._compute_equity_ratios(
        net_income=1_000_000_000, total_equity=39_000_000_000,
        total_debt=30_000_000_000, market_cap=None,
        average_equity=38_000_000_000, average_assets=74_000_000_000,
        financial_currency="USD", quote_currency="USD", info_price_to_book=1.49,
    )
    assert ratios["pb_ratio"] == 1.49


def test_compute_equity_ratios_same_currency_no_fallback_triggered():
    """financial_currency == quote_currency (the normal domestic case) must
    still compute P/B directly from market_cap/total_equity, not fall back."""
    ratios = YFinanceClient._compute_equity_ratios(
        net_income=100_000_000, total_equity=500_000_000,
        total_debt=400_000_000, market_cap=5_000_000_000,
        average_equity=480_000_000, average_assets=2_000_000_000,
        financial_currency="USD", quote_currency="USD", info_price_to_book=999.0,
    )
    assert ratios["pb_ratio"] == round(5_000_000_000 / 500_000_000, 2)
    assert ratios["pb_ratio"] != 999.0
    assert ratios["pb_ratio_basis"] == "computed"


def test_compute_equity_ratios_zero_equity_no_division_by_zero():
    ratios = YFinanceClient._compute_equity_ratios(
        net_income=10_000_000, total_equity=0,
        total_debt=20_000_000, market_cap=500_000_000,
        average_equity=0, average_assets=100_000_000,
    )
    assert ratios["debt_to_equity"] is None
    assert ratios["roe"] is None
    assert ratios["pb_ratio"] is None
    assert ratios["roa"] == round(10_000_000 / 100_000_000, 4)


# ---------------------------------------------------------------------
# FinancialsAgent._format_fundamentals - N/A (negative equity) rendering
# ---------------------------------------------------------------------

def make_raw_fundamentals(total_equity, average_equity=None, **overrides):
    if average_equity is None:
        average_equity = total_equity
    data = {
        "ticker": "TEST",
        "sector": "Technology",
        "revenue": 1_000_000_000,
        "net_income": 50_000_000,
        "total_assets": 800_000_000,
        "total_liabilities": 800_000_000 - total_equity,
        "total_equity": total_equity,
        "total_debt": 300_000_000,
        "cash": 100_000_000,
        "free_cash_flow": 40_000_000,
        "operating_cash_flow": 60_000_000,
        "gross_margin": 0.5,
        "operating_margin": 0.2,
        "profit_margin": 0.05,
        "eps": 1.5,
        "pe_ratio": 20.0,
        "dividend_yield": None,
        "current_ratio": 1.2,
        "quick_ratio": 1.0,
        "financials_period_end": "2026-06-30",
        "balance_sheet_period_end": "2026-06-30",
    }
    equity_ratios = YFinanceClient._compute_equity_ratios(
        net_income=data["net_income"], total_equity=total_equity,
        total_debt=data["total_debt"], market_cap=5_000_000_000,
        average_equity=average_equity, average_assets=data["total_assets"],
    )
    data.update(equity_ratios)
    data.update(overrides)
    return data


def test_format_fundamentals_negative_equity_renders_na():
    agent = FinancialsAgent()
    formatted = agent._format_fundamentals(
        make_raw_fundamentals(total_equity=-200_000_000, average_equity=-180_000_000)
    )

    assert formatted["negative_equity"] is True
    assert formatted["debt_to_equity"] == "N/A (negative equity)"
    assert formatted["pb_ratio"] == "N/A (negative equity)"
    assert formatted["roe"] == "N/A (negative equity)"
    # ROA is unaffected by equity sign and should still render a real number
    assert formatted["roa"] != "N/A (negative equity)"


def test_format_fundamentals_positive_equity_renders_normally():
    agent = FinancialsAgent()
    formatted = agent._format_fundamentals(
        make_raw_fundamentals(total_equity=500_000_000, average_equity=480_000_000)
    )

    assert formatted["negative_equity"] is False
    assert formatted["debt_to_equity"] != "N/A (negative equity)"
    assert formatted["pb_ratio"] != "N/A (negative equity)"
    assert formatted["roe"] != "N/A (negative equity)"


# ---------------------------------------------------------------------
# Sector gating: financial-sector metrics unconditionally N/A; is_reit flag
# ---------------------------------------------------------------------

def test_financial_sector_gates_gross_and_liquidity_ratios_unconditionally():
    """A bank/insurer must show gross margin and current/quick ratios as N/A
    EVEN WHEN yfinance populated real-looking values for them - they aren't
    meaningful for the sector, and the page's own disclaimer says so. The
    previous gate only fired when the value was already missing, so a
    populated value leaked through and contradicted the disclaimer."""
    agent = FinancialsAgent()
    data = make_raw_fundamentals(
        total_equity=50_000_000_000, average_equity=48_000_000_000,
        sector="Financial Services",
        gross_margin=0.62, current_ratio=1.35, quick_ratio=1.10,  # yfinance-populated
    )
    formatted = agent._format_fundamentals(data)

    assert formatted["is_financial_sector"] is True
    assert formatted["is_reit"] is False
    assert formatted["gross_margin"] == "N/A"
    assert formatted["current_ratio"] == "N/A"
    assert formatted["quick_ratio"] == "N/A"


def test_reit_sector_sets_is_reit_flag():
    agent = FinancialsAgent()
    formatted = agent._format_fundamentals(
        make_raw_fundamentals(total_equity=50_000_000_000, average_equity=48_000_000_000,
                              sector="Real Estate")
    )
    assert formatted["is_reit"] is True
    assert formatted["is_financial_sector"] is False


def test_non_financial_non_reit_sector_keeps_ratios_and_flags_false():
    """A normal operating company must keep its real gross margin and
    liquidity ratios, and neither sector flag fires."""
    agent = FinancialsAgent()
    formatted = agent._format_fundamentals(
        make_raw_fundamentals(total_equity=500_000_000, average_equity=480_000_000,
                              sector="Technology", gross_margin=0.5,
                              current_ratio=1.2, quick_ratio=1.0)
    )
    assert formatted["is_financial_sector"] is False
    assert formatted["is_reit"] is False
    assert formatted["gross_margin"] != "N/A"
    assert formatted["current_ratio"] != "N/A"


# ---------------------------------------------------------------------
# RiskAgent - Negative Shareholders' Equity flag
# ---------------------------------------------------------------------

def run_risk_agent_for_equity(total_equity, average_equity=None):
    fin_agent = FinancialsAgent()
    formatted = fin_agent._format_fundamentals(
        make_raw_fundamentals(total_equity=total_equity, average_equity=average_equity)
    )
    fundamentals_data = {"ticker": "TEST", "success": True, "fundamentals": formatted}

    analysis_data = {
        "market_data": {}, "fundamentals_data": fundamentals_data, "news_data": {},
        "company_info": {"sector": "Technology", "company_name": "Test Co"},
        "macro_data": {}, "financing_data": {},
    }
    return RiskAgent().run("TEST", analysis_data)


def test_negative_equity_triggers_high_severity_risk_flag():
    result = run_risk_agent_for_equity(total_equity=-200_000_000, average_equity=-180_000_000)
    titles = {r["title"]: r for r in result["risks"]}

    assert "Negative Shareholders' Equity" in titles
    assert titles["Negative Shareholders' Equity"]["severity"] == "High"


def test_positive_equity_does_not_trigger_negative_equity_flag():
    result = run_risk_agent_for_equity(total_equity=500_000_000, average_equity=480_000_000)
    titles = {r["title"] for r in result["risks"]}
    assert "Negative Shareholders' Equity" not in titles


# ---------------------------------------------------------------------
# FX-invariance: ROE/ROA must be identical whether computed entirely in
# home currency or through the full USD-converting pipeline. Both
# numerator (net_income) and denominator (average_equity/average_assets)
# must be converted by the *same* rate for this to hold - if a future
# change converted them by different rates (e.g. each period's own
# historical rate before averaging, rather than the current shared rate
# applied uniformly after averaging), real FX movement would leak into
# what should be a pure, currency-invariant operating ratio.
# ---------------------------------------------------------------------

class FakeInfo(dict):
    """dict subclass so `stock.info` behaves like the real yfinance API."""


class FakeTicker:
    def __init__(self, info, quarterly_balance_sheet, quarterly_cashflow):
        self.info = FakeInfo(info)
        self.quarterly_balance_sheet = quarterly_balance_sheet
        self.balance_sheet = None
        self.quarterly_cashflow = quarterly_cashflow
        self.cashflow = None


def make_fake_foreign_issuer(net_income_native, equity_q0, equity_q4, assets_q0, assets_q4):
    """A minimal foreign-issuer fixture: financials in JPY, quote in USD,
    with distinct Q0/Q4 equity and assets so the year-ago average is
    meaningful (mirrors Item A's fixture). Uses real Timestamp columns,
    ~91 days apart (matching real yfinance data shape), since the date-
    gap tolerance check needs to subtract them."""
    end = pd.Timestamp("2026-06-30")
    dates = [end - pd.DateOffset(days=91 * i) for i in range(5)]
    mid_equity = (equity_q0 + equity_q4) / 2
    mid_assets = (assets_q0 + assets_q4) / 2
    quarterly_balance_sheet = pd.DataFrame(
        {"Stockholders Equity": [equity_q0, mid_equity, mid_equity, mid_equity, equity_q4],
         "Total Assets": [assets_q0, mid_assets, mid_assets, mid_assets, assets_q4]},
        index=dates,
    ).T
    quarterly_cashflow = pd.DataFrame(
        {"Operating Cash Flow": [1_000_000_000] * 4, "Free Cash Flow": [800_000_000] * 4},
        index=dates[:4],
    ).T
    info = {
        "sector": "Consumer Cyclical",
        "totalRevenue": net_income_native * 5,
        "netIncomeToCommon": net_income_native,
        "totalAssets": None, "totalLiabilities": None, "totalEquity": None, "totalDebt": None,
        "totalCash": 10_000_000_000,
        "operatingCashflow": None, "freeCashflow": None,
        "grossMargins": 0.2, "operatingMargins": 0.1, "profitMargins": 0.08,
        "trailingEps": 10.0, "trailingPE": 8.0, "priceToBook": 999.0,  # deliberately implausible - must not be used
        "dividendYield": 2.0,
        "debtToEquity": None, "currentRatio": None, "quickRatio": None,
        "mostRecentQuarter": 1780000000,
        "marketCap": 200_000_000_000,  # USD
        "financialCurrency": "JPY",
        "currency": "USD",
    }
    return FakeTicker(info, quarterly_balance_sheet, quarterly_cashflow)


def make_fake_issuer_with_preferred_stock(
    net_income_to_common, stockholders_equity_q0, stockholders_equity_q4,
    common_stock_equity_q0, common_stock_equity_q4,
    total_equity_gmi_q0=None, total_equity_gmi_q4=None,
):
    """Domestic (USD) issuer fixture with distinct Stockholders Equity vs
    Common Stock Equity (the gap being real preferred stock) vs Total
    Equity Gross Minority Interest - to confirm ROE's average prefers
    Common Stock Equity specifically, while total_equity (the Balance
    Sheet card's headline figure) keeps preferring Stockholders Equity."""
    if total_equity_gmi_q0 is None:
        total_equity_gmi_q0 = stockholders_equity_q0
    if total_equity_gmi_q4 is None:
        total_equity_gmi_q4 = stockholders_equity_q4

    end = pd.Timestamp("2026-06-30")
    dates = [end - pd.DateOffset(days=91 * i) for i in range(5)]
    mid_se = (stockholders_equity_q0 + stockholders_equity_q4) / 2
    mid_cse = (common_stock_equity_q0 + common_stock_equity_q4) / 2
    mid_gmi = (total_equity_gmi_q0 + total_equity_gmi_q4) / 2
    quarterly_balance_sheet = pd.DataFrame(
        {
            "Stockholders Equity": [stockholders_equity_q0, mid_se, mid_se, mid_se, stockholders_equity_q4],
            "Common Stock Equity": [common_stock_equity_q0, mid_cse, mid_cse, mid_cse, common_stock_equity_q4],
            "Total Equity Gross Minority Interest": [total_equity_gmi_q0, mid_gmi, mid_gmi, mid_gmi, total_equity_gmi_q4],
            "Total Assets": [stockholders_equity_q0 * 3] * 5,
        },
        index=dates,
    ).T
    quarterly_cashflow = pd.DataFrame(
        {"Operating Cash Flow": [100_000_000] * 4, "Free Cash Flow": [80_000_000] * 4},
        index=dates[:4],
    ).T
    info = {
        "sector": "Financial Services",
        "totalRevenue": net_income_to_common * 5,
        "netIncomeToCommon": net_income_to_common,
        "totalAssets": None, "totalLiabilities": None, "totalEquity": None, "totalDebt": None,
        "totalCash": 1_000_000_000,
        "operatingCashflow": None, "freeCashflow": None,
        "grossMargins": None, "operatingMargins": 0.5, "profitMargins": 0.3,
        "trailingEps": 10.0, "trailingPE": 12.0, "priceToBook": 1.5,
        "dividendYield": 2.0,
        "debtToEquity": None, "currentRatio": None, "quickRatio": None,
        "mostRecentQuarter": 1780000000,
        "marketCap": 400_000_000_000,
        "financialCurrency": "USD",
        "currency": "USD",
    }
    return FakeTicker(info, quarterly_balance_sheet, quarterly_cashflow)


def test_roe_uses_common_stock_equity_not_stockholders_equity(monkeypatch):
    """ROE's denominator must prefer Common Stock Equity (matching
    net_income's to-common scope) over Stockholders Equity/Total Equity
    Gross Minority Interest, both of which still include preferred stock.
    total_equity (the Balance Sheet card's headline figure) must NOT
    change - it's a different concept (total equity, not common-only) and
    correctly keeps preferring Stockholders Equity."""
    import data_sources.yfinance_client as yfinance_client_module

    net_income_to_common = 10_000_000_000
    stockholders_equity_q0, stockholders_equity_q4 = 120_000_000_000, 100_000_000_000
    common_stock_equity_q0, common_stock_equity_q4 = 100_000_000_000, 80_000_000_000
    # distinct from both of the above, to prove neither is accidentally used
    total_equity_gmi_q0, total_equity_gmi_q4 = 125_000_000_000, 105_000_000_000

    fake_ticker = make_fake_issuer_with_preferred_stock(
        net_income_to_common, stockholders_equity_q0, stockholders_equity_q4,
        common_stock_equity_q0, common_stock_equity_q4,
        total_equity_gmi_q0, total_equity_gmi_q4,
    )
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: fake_ticker)
    client = YFinanceClient()
    fundamentals = client.get_fundamentals("FAKE")

    expected_roe = round(net_income_to_common / ((common_stock_equity_q0 + common_stock_equity_q4) / 2), 4)
    assert fundamentals["equity_average_row"] == "Common Stock Equity"
    assert round(fundamentals["roe"], 4) == expected_roe

    # Headline total_equity is untouched - still Stockholders Equity, the
    # existing, correct point-in-time basis for the balance-sheet card.
    assert fundamentals["total_equity"] == stockholders_equity_q0


def test_jpm_shaped_preferred_stock_fixture_locks_in_observed_delta(monkeypatch):
    """Real JPM magnitudes (Stockholders Equity includes ~$21B of preferred
    stock absent from Common Stock Equity). Locks in the investigation's
    finding: switching to Common Stock Equity does NOT close JPM's gap to
    Yahoo's reported returnOnEquity (0.17789) - it's a real, separate
    divergence in Yahoo's own methodology, not explained by preferred
    stock alone. The gap is larger with the (correct) common-equity basis
    than it was with the old Stockholders-Equity basis (~0.39pp)."""
    import data_sources.yfinance_client as yfinance_client_module

    net_income_to_common = 63_634_001_920
    se_q0, se_q4 = 374_598_000_000, 356_924_000_000
    cse_q0, cse_q4 = 353_558_000_000, 336_879_000_000

    fake_ticker = make_fake_issuer_with_preferred_stock(net_income_to_common, se_q0, se_q4, cse_q0, cse_q4)
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: fake_ticker)
    client = YFinanceClient()
    fundamentals = client.get_fundamentals("JPM")

    expected_roe_common = round(net_income_to_common / ((cse_q0 + cse_q4) / 2), 4)
    assert fundamentals["equity_average_row"] == "Common Stock Equity"
    assert round(fundamentals["roe"], 4) == expected_roe_common

    yahoo_roe = 0.17789
    assert abs(expected_roe_common - yahoo_roe) > 0.005  # ~0.64pp gap - not closed by this fix


def test_pgr_shaped_no_preferred_stock_fixture_is_unaffected(monkeypatch):
    """PGR carries no preferred stock - Stockholders Equity and Common
    Stock Equity are identical, so this fix is a complete no-op: same
    result as before, still matching Yahoo's reported ROE closely."""
    import data_sources.yfinance_client as yfinance_client_module

    net_income_to_common = 11_694_999_552
    equity_q0, equity_q4 = 34_333_000_000, 32_604_000_000  # identical for both concepts

    fake_ticker = make_fake_issuer_with_preferred_stock(net_income_to_common, equity_q0, equity_q4, equity_q0, equity_q4)
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: fake_ticker)
    client = YFinanceClient()
    fundamentals = client.get_fundamentals("PGR")

    expected_roe = round(net_income_to_common / ((equity_q0 + equity_q4) / 2), 4)
    assert round(fundamentals["roe"], 4) == expected_roe

    yahoo_roe = 0.349430
    assert abs(expected_roe - yahoo_roe) < 0.001  # matches closely, unaffected by this fix


def test_citigroup_shaped_preferred_stock_fixture_confirms_fix_narrows_gap(monkeypatch):
    """Citigroup carries the largest preferred-stock share of the banks
    surveyed live (~9.2% of Stockholders Equity: ~$19.6B preferred, vs JPM's
    ~5.6%). This is the case the common-equity fix was built for, and unlike
    JPM it behaves exactly as intended: switching ROE's denominator from
    Stockholders Equity (which still includes the preferred) to Common Stock
    Equity moves the ratio much CLOSER to Yahoo's reported returnOnEquity
    (0.08529) - the gap shrinks from ~0.79pp to ~0.07pp (~10x). Yahoo's own
    implied equity base (net income / returnOnEquity ~= $193.0B) lands on the
    average Common Stock Equity (~$194.7B), NOT the Stockholders Equity base
    (~$212.6B) - independent corroboration that the common-equity basis is
    the correct one and that JPM's non-closing residual is a JPM-specific
    quirk, not a flaw in the fix."""
    import data_sources.yfinance_client as yfinance_client_module

    net_income_to_common = 16_460_000_256
    se_q0, se_q4 = 212_015_000_000, 213_222_000_000
    cse_q0, cse_q4 = 192_465_000_000, 196_872_000_000

    fake_ticker = make_fake_issuer_with_preferred_stock(net_income_to_common, se_q0, se_q4, cse_q0, cse_q4)
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: fake_ticker)
    client = YFinanceClient()
    fundamentals = client.get_fundamentals("C")

    expected_roe_common = round(net_income_to_common / ((cse_q0 + cse_q4) / 2), 4)
    assert fundamentals["equity_average_row"] == "Common Stock Equity"
    assert round(fundamentals["roe"], 4) == expected_roe_common

    # Headline total_equity untouched - still Stockholders Equity point-in-time.
    assert fundamentals["total_equity"] == se_q0

    # The core stress-test assertion: for a large-preferred-stock filer the
    # common-equity basis lands much closer to Yahoo's reported ROE than the
    # old stockholders-equity basis would - here by well over 5x - which is
    # what distinguishes this from JPM (where the fix widened the gap).
    yahoo_roe = 0.085290
    roe_stockholders = net_income_to_common / ((se_q0 + se_q4) / 2)
    roe_common = net_income_to_common / ((cse_q0 + cse_q4) / 2)
    assert abs(roe_common - yahoo_roe) < abs(roe_stockholders - yahoo_roe) / 5


def test_roe_roa_are_fx_invariant_through_the_real_pipeline(monkeypatch):
    """Exercises the actual get_fundamentals code path (not a
    reimplementation) with two DIFFERENT FX rates, to prove the shared-rate
    conversion cancels out algebraically rather than merely by coincidence
    of using one fixed rate in every test."""
    import data_sources.yfinance_client as yfinance_client_module

    net_income_native = 3_000_000_000_000  # JPY
    equity_q0, equity_q4 = 37_000_000_000_000, 30_000_000_000_000  # JPY, distinct
    assets_q0, assets_q4 = 90_000_000_000_000, 80_000_000_000_000  # JPY, distinct

    expected_roe_native = round(net_income_native / ((equity_q0 + equity_q4) / 2), 4)
    expected_roa_native = round(net_income_native / ((assets_q0 + assets_q4) / 2), 4)

    for fx_rate in (0.0063, 0.0091):  # two different rates - must not change the ratio
        YFinanceClient._cache.clear()  # same ticker each iteration; don't serve the first from cache
        fake_ticker = make_fake_foreign_issuer(net_income_native, equity_q0, equity_q4, assets_q0, assets_q4)
        monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: fake_ticker)

        client = YFinanceClient()
        monkeypatch.setattr(
            client.fred_client, "get_fx_rate_to_usd",
            lambda currency, _rate=fx_rate: {"rate": _rate, "as_of": "2026-07-31"},
        )

        fundamentals = client.get_fundamentals("FAKE")

        assert fundamentals["fx_conversion"]["applied"] is True
        assert round(fundamentals["roe"], 4) == expected_roe_native
        assert round(fundamentals["roa"], 4) == expected_roa_native
        # P/B must come from the direct (FX-converted) computation, not the
        # deliberately-implausible info_price_to_book fallback set above
        assert fundamentals["pb_ratio_basis"] == "computed"
        assert fundamentals["pb_ratio"] != 999.0


# ---------------------------------------------------------------------
# profit_margin is computed locally (net income to common / revenue), NOT
# read from info.profitMargins, which the 100-ticker sweep found wrong/stale
# (0.0 while real, or the wrong sign) for 6 tickers.
# ---------------------------------------------------------------------

def make_fake_ticker_for_profit_margin(revenue, net_income_to_common, yf_profit_margins):
    """Minimal domestic (USD) issuer where info.profitMargins deliberately
    disagrees with net income / revenue, so the test proves the local
    computation wins over the precomputed field."""
    end = pd.Timestamp("2026-06-30")
    dates = [end - pd.DateOffset(days=91 * i) for i in range(5)]
    qbs = pd.DataFrame(
        {"Stockholders Equity": [1_000_000_000] * 5, "Common Stock Equity": [1_000_000_000] * 5,
         "Total Assets": [3_000_000_000] * 5},
        index=dates,
    ).T
    qcf = pd.DataFrame(
        {"Operating Cash Flow": [100_000_000] * 4, "Free Cash Flow": [80_000_000] * 4},
        index=dates[:4],
    ).T
    info = {
        "sector": "Technology",
        "totalRevenue": revenue, "netIncomeToCommon": net_income_to_common,
        "profitMargins": yf_profit_margins,  # deliberately disagrees with NI/Rev
        "grossMargins": 0.4, "operatingMargins": 0.2,
        "totalAssets": None, "totalLiabilities": None, "totalEquity": None, "totalDebt": None,
        "totalCash": 100_000_000, "operatingCashflow": None, "freeCashflow": None,
        "trailingEps": 1.0, "trailingPE": 10.0, "priceToBook": 1.5, "dividendYield": 1.0,
        "debtToEquity": None, "currentRatio": None, "quickRatio": None,
        "mostRecentQuarter": 1780000000, "marketCap": 10_000_000_000,
        "financialCurrency": "USD", "currency": "USD",
    }
    return FakeTicker(info, qbs, qcf)


def test_profit_margin_computed_locally_not_from_info(monkeypatch):
    import data_sources.yfinance_client as yfinance_client_module
    # info says 0% margin; net income / revenue says 15%.
    fake = make_fake_ticker_for_profit_margin(
        revenue=1_000_000_000, net_income_to_common=150_000_000, yf_profit_margins=0.0)
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: fake)
    f = YFinanceClient().get_fundamentals("FAKE")
    assert f["profit_margin"] == 150_000_000 / 1_000_000_000  # 0.15
    assert f["profit_margin"] != 0.0  # the wrong precomputed value


def test_profit_margin_koksf_fixture(monkeypatch):
    """Real KOKSF magnitudes: info.profitMargins=0.0 while the real margin is
    ~13.5%. Locks in that the local computation replaces the broken field."""
    import data_sources.yfinance_client as yfinance_client_module
    revenue, ni = 258_703_998_976, 34_880_999_424
    fake = make_fake_ticker_for_profit_margin(revenue, ni, yf_profit_margins=0.0)
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: fake)
    f = YFinanceClient().get_fundamentals("KOKSF")
    assert round(f["profit_margin"], 4) == round(ni / revenue, 4) == 0.1348
    assert f["profit_margin"] != 0.0


def test_profit_margin_sony_fixture_sign_corrected(monkeypatch):
    """Real SONY magnitudes: info.profitMargins=-0.01746 (NEGATIVE) while the
    real margin is +8.8% (POSITIVE). Locks in that the sign is corrected."""
    import data_sources.yfinance_client as yfinance_client_module
    revenue, ni = 12_695_775_477_760, 1_114_027_065_344
    fake = make_fake_ticker_for_profit_margin(revenue, ni, yf_profit_margins=-0.01746)
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: fake)
    f = YFinanceClient().get_fundamentals("SONY")
    assert round(f["profit_margin"], 4) == round(ni / revenue, 4)
    assert f["profit_margin"] > 0  # corrected from the negative precomputed value


def test_profit_margin_none_when_revenue_missing_or_zero(monkeypatch):
    import data_sources.yfinance_client as yfinance_client_module
    for revenue in (0, None):
        fake = make_fake_ticker_for_profit_margin(revenue, 150_000_000, yf_profit_margins=0.3)
        monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: fake)
        f = YFinanceClient().get_fundamentals("FAKE")
        assert f["profit_margin"] is None


# ---------------------------------------------------------------------
# gross_margin / operating_margin are recomputed as a TTM ratio from the
# income statement (NOT Yahoo's precomputed grossMargins/operatingMargins,
# which the sweep + SEC corroboration found wrong for MRNA), falling back to
# the precomputed value only when the statement can't support a recompute.
# ---------------------------------------------------------------------

def make_income_stmt_fake(revenue_q, gross_profit_q, operating_income_q,
                          yf_gross, yf_operating):
    """Fake with a quarterly income statement so _ttm_margin recomputes gross/
    operating margin locally. Lists are most-recent-first; TTM = sum of 4."""
    n = len(revenue_q)
    end = pd.Timestamp("2026-06-30")
    idates = [end - pd.DateOffset(days=91 * i) for i in range(n)]
    qis = pd.DataFrame(
        {"Total Revenue": revenue_q, "Gross Profit": gross_profit_q,
         "Operating Income": operating_income_q},
        index=idates,
    ).T
    bdates = [end - pd.DateOffset(days=91 * i) for i in range(5)]
    qbs = pd.DataFrame(
        {"Stockholders Equity": [1_000_000_000] * 5, "Common Stock Equity": [1_000_000_000] * 5,
         "Total Assets": [3_000_000_000] * 5},
        index=bdates,
    ).T
    qcf = pd.DataFrame(
        {"Operating Cash Flow": [100_000_000] * 4, "Free Cash Flow": [80_000_000] * 4},
        index=bdates[:4],
    ).T
    info = {
        "sector": "Healthcare", "totalRevenue": sum(revenue_q), "netIncomeToCommon": -1_000_000_000,
        "profitMargins": -0.4, "grossMargins": yf_gross, "operatingMargins": yf_operating,
        "totalAssets": None, "totalLiabilities": None, "totalEquity": None, "totalDebt": None,
        "totalCash": 100_000_000, "operatingCashflow": None, "freeCashflow": None,
        "trailingEps": -1.0, "trailingPE": None, "priceToBook": 3.0, "dividendYield": None,
        "debtToEquity": None, "currentRatio": None, "quickRatio": None,
        "mostRecentQuarter": 1780000000, "marketCap": 30_000_000_000,
        "financialCurrency": "USD", "currency": "USD",
    }
    ticker = FakeTicker(info, qbs, qcf)
    ticker.quarterly_income_stmt = qis  # FakeTicker lacks this attr by default
    return ticker


def test_mrna_gross_operating_margin_recomputed_from_filings(monkeypatch):
    """MRNA's real filed quarterly figures ($, most-recent-first over the TTM
    window 2026-06-30 .. 2025-09-30), SEC-XBRL corroborated. The local TTM
    recompute gives +22.8% gross / -150% operating; Yahoo's precomputed -66% /
    -558% are impossible against these filings and must NOT be used."""
    import data_sources.yfinance_client as yfinance_client_module
    revenue = [143_000_000, 389_000_000, 676_000_000, 1_002_000_000]   # TTM 2,210M
    gross = [50_000_000, -566_000_000, 224_000_000, 795_000_000]        # TTM +503M
    oper = [-815_000_000, -1_388_000_000, -857_000_000, -260_000_000]   # TTM -3,320M
    fake = make_income_stmt_fake(revenue, gross, oper, yf_gross=-0.66023, yf_operating=-5.5793)
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: fake)
    f = YFinanceClient().get_fundamentals("MRNA")

    assert f["gross_margin_basis"] == "computed"
    assert round(f["gross_margin"], 4) == round(503_000_000 / 2_210_000_000, 4) == 0.2276
    assert f["gross_margin"] > 0  # NOT Yahoo's negative -0.66
    assert f["operating_margin_basis"] == "computed"
    assert round(f["operating_margin"], 4) == round(-3_320_000_000 / 2_210_000_000, 4)
    assert f["operating_margin"] > -5.0  # NOT Yahoo's impossible -5.58


def test_gross_operating_margin_fall_back_to_info_without_income_statement(monkeypatch):
    """No quarterly income statement (thin OTC micro-cap) -> the recompute
    isn't possible, so it falls back to Yahoo's precomputed value, labeled."""
    import data_sources.yfinance_client as yfinance_client_module
    fake = make_fake_ticker_for_profit_margin(1_000_000_000, 100_000_000, yf_profit_margins=0.1)
    fake.info["grossMargins"] = 0.55
    fake.info["operatingMargins"] = 0.30
    # make_fake_ticker_for_profit_margin builds no quarterly_income_stmt attr
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: fake)
    f = YFinanceClient().get_fundamentals("FAKE")
    assert f["gross_margin_basis"] == "info_fallback"
    assert f["gross_margin"] == 0.55
    assert f["operating_margin_basis"] == "info_fallback"
    assert f["operating_margin"] == 0.30


def test_gross_margin_falls_back_when_gross_profit_exceeds_revenue(monkeypatch):
    """STRG-shaped garbage: reported 'Gross Profit' ($29) exceeds revenue
    ($21), an impossible >100% margin -> reject the recompute and fall back to
    the precomputed value rather than display a nonsensical figure."""
    import data_sources.yfinance_client as yfinance_client_module
    revenue = [21, 21, 21, 21]
    gross = [29, 29, 29, 29]                 # > revenue -> impossible
    oper = [-75_973, -75_973, -75_973, -75_973]
    fake = make_income_stmt_fake(revenue, gross, oper, yf_gross=0.0, yf_operating=-3617.0)
    monkeypatch.setattr(yfinance_client_module.yf, "Ticker", lambda ticker: fake)
    f = YFinanceClient().get_fundamentals("STRG")
    assert f["gross_margin_basis"] == "info_fallback"
    assert f["gross_margin"] == 0.0  # Yahoo's value, not the impossible 138%
