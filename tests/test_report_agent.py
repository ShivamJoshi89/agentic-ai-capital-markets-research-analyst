"""
Tests for ReportAgent's currency disclosure in the LLM context. All
synthetic - no network/OpenAI access required (only the pure static
formatting method is exercised).
"""

import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import agents.report_agent as report_agent_module
from agents.report_agent import ReportAgent


def test_format_currency_note_empty_for_ordinary_usd_reporter():
    fundamentals_data = {"fundamentals": {"fx_conversion": {"applied": False, "native_currency": "USD"}}}
    assert ReportAgent._format_currency_note(fundamentals_data) == ""


def test_format_currency_note_discloses_conversion_when_applied():
    fundamentals_data = {
        "fundamentals": {
            "fx_conversion": {
                "applied": True, "from_currency": "JPY", "to_currency": "USD",
                "rate": 0.0062829856747926615, "rate_as_of": "2026-07-31",
            }
        }
    }
    note = ReportAgent._format_currency_note(fundamentals_data)
    assert "JPY" in note
    assert "USD" in note
    assert "2026-07-31" in note


def test_format_currency_note_flags_unconverted_foreign_currency():
    fundamentals_data = {"fundamentals": {"fx_conversion": {"applied": False, "native_currency": "KRW"}}}
    note = ReportAgent._format_currency_note(fundamentals_data)
    assert "KRW" in note
    assert "no USD conversion rate was available" in note


def test_format_currency_note_handles_missing_fx_conversion_key():
    """Defensive: a caller that never set fx_conversion at all (e.g. an
    older cached payload) must not raise - treated as the ordinary USD case."""
    assert ReportAgent._format_currency_note({"fundamentals": {}}) == ""
    assert ReportAgent._format_currency_note({}) == ""


def test_format_financing_does_not_emit_burn_runway_for_exempt_sector():
    """The LLM-facing financing note must not hand the model a burn-rate cash
    runway for a bank/insurer/REIT (structural negative OCF) - it states the
    balance-sheet trend instead."""
    agent = ReportAgent.__new__(ReportAgent)  # no OpenAI client needed for this pure method
    financing = {
        "success": True, "overhang_level": "Low",
        "dilution": {"available": True, "yoy_change_pct": 1.0},
        "cash_runway": {"available": True, "cash_flow_positive": False, "runway_months": 6.0,
                        "sector_exempt": True, "total_assets_yoy_change_pct": 10.2},
        "financing_filings": [],
    }
    text = agent._format_financing(financing)
    assert "Estimated Cash Runway" not in text
    assert "Operating Cash Flow: Negative" in text


def test_format_financing_flags_contraction_for_shrinking_exempt_sector():
    agent = ReportAgent.__new__(ReportAgent)
    financing = {
        "success": True, "overhang_level": "Low",
        "dilution": {"available": True, "yoy_change_pct": 1.0},
        "cash_runway": {"available": True, "cash_flow_positive": False, "runway_months": 6.0,
                        "sector_exempt": True, "total_assets_yoy_change_pct": -8.0},
        "financing_filings": [],
    }
    text = agent._format_financing(financing)
    assert "down 8.0% YoY" in text
    assert "Estimated Cash Runway" not in text


def test_format_financing_still_emits_runway_for_non_exempt():
    agent = ReportAgent.__new__(ReportAgent)
    financing = {
        "success": True, "overhang_level": "Medium",
        "dilution": {"available": True, "yoy_change_pct": 1.0},
        "cash_runway": {"available": True, "cash_flow_positive": False, "runway_months": 6.0,
                        "sector_exempt": False},
        "financing_filings": [],
    }
    text = agent._format_financing(financing)
    assert "Estimated Cash Runway: ~6 months" in text


def test_valuation_caveats_reit():
    """A REIT must carry the FFO/AFFO caveat so the LLM doesn't editorialize
    the depreciation-inflated GAAP P/E as a 'premium valuation' (both models
    did exactly that when the caveat was absent)."""
    note = ReportAgent._valuation_caveats({"fundamentals": {"is_reit": True}})
    assert "REIT" in note
    assert "FFO/AFFO" in note
    assert "premium valuation" in note.lower()


def test_valuation_caveats_financial_and_negative_equity():
    fin = ReportAgent._valuation_caveats({"fundamentals": {"is_financial_sector": True}})
    assert "Bank/insurer" in fin
    neg = ReportAgent._valuation_caveats({"fundamentals": {"negative_equity": True}})
    assert "Negative shareholders' equity" in neg
    assert "ROE" in neg


def test_valuation_caveats_empty_for_ordinary_company():
    assert ReportAgent._valuation_caveats({"fundamentals": {"sector": "Technology"}}) == ""
    assert ReportAgent._valuation_caveats({}) == ""


def test_prepare_context_includes_reit_caveat(monkeypatch):
    agent, _ = _make_agent_with_fake_client(monkeypatch)
    outputs = _sample_outputs()
    outputs["fundamentals_data"]["fundamentals"]["is_reit"] = True
    context = agent._prepare_context("O", outputs)
    assert "SECTOR/VALUATION CAVEATS" in context
    assert "FFO/AFFO" in context


def test_valuation_caveats_flags_unverified_margin():
    """Provenance surfacing: when gross/operating margin fell back to Yahoo's
    precomputed value (basis 'info_fallback'), the LLM context must say so."""
    note = ReportAgent._valuation_caveats(
        {"fundamentals": {"gross_margin_basis": "info_fallback", "gross_margin": "12.34%"}})
    assert "may be unreliable" in note


def test_valuation_caveats_no_margin_flag_when_computed_or_na():
    # locally computed -> no caveat
    assert ReportAgent._valuation_caveats(
        {"fundamentals": {"gross_margin_basis": "computed", "gross_margin": "40.00%"}}) == ""
    # financial-sector N/A margin (even with info_fallback basis) -> no caveat
    assert ReportAgent._valuation_caveats(
        {"fundamentals": {"gross_margin_basis": "info_fallback", "gross_margin": "N/A",
                          "operating_margin_basis": "info_fallback", "operating_margin": "N/A"}}) == ""


def test_prepare_context_surfaces_currency_and_ytd_provenance(monkeypatch):
    """Representative FX-converted foreign issuer: the currency-conversion and
    ytd-basis provenance must actually appear in the LLM context string, not
    just the raw API response."""
    agent, _ = _make_agent_with_fake_client(monkeypatch)
    outputs = _sample_outputs()
    outputs["fundamentals_data"]["fundamentals"]["fx_conversion"] = {
        "applied": True, "from_currency": "JPY", "to_currency": "USD",
        "rate": 0.0066, "rate_as_of": "2026-08-07"}
    outputs["market_data"]["metrics"]["ytd_basis"] = "trailing_since_series_start"
    context = agent._prepare_context("TM", outputs)
    assert "Converted from JPY to USD" in context           # fx_conversion provenance
    assert "trailing since series start" in context          # ytd_basis provenance


def test_generate_memo_uses_configured_model_and_completion_tokens(monkeypatch):
    """The swap must actually take effect: the configured model is sent, via
    max_completion_tokens (gpt-5.x rejects max_tokens)."""
    agent, holder = _make_agent_with_fake_client(monkeypatch)
    agent._generate_memo_with_llm("BIGCO", "some context", "BigCo")
    sink = holder["client"].sink
    assert sink["model"] == ReportAgent.LLM_MODEL
    assert "max_completion_tokens" in sink["kwargs"]
    assert "max_tokens" not in sink["kwargs"]


def test_ytd_line_labeled_ytd_for_calendar_basis():
    market_data = {"metrics": {"ytd_return": 12.34, "ytd_basis": "calendar_ytd"}}
    line = ReportAgent._format_ytd_line(market_data)
    assert line == "YTD Return: 12.34%"


def test_ytd_line_relabeled_for_trailing_fallback():
    """Early-January fallback: the figure is a trailing return, not calendar
    YTD, and must not be narrated to the LLM as 'YTD Return'."""
    market_data = {"metrics": {"ytd_return": 5.0, "ytd_basis": "trailing_since_series_start"}}
    line = ReportAgent._format_ytd_line(market_data)
    assert "YTD Return:" not in line
    assert "trailing" in line.lower()
    assert "5.0%" in line


def test_ytd_line_defaults_to_ytd_when_basis_missing():
    """An older payload without ytd_basis must not raise and defaults to the
    plain YTD label (matching the pre-existing field name)."""
    assert ReportAgent._format_ytd_line({"metrics": {"ytd_return": 1.0}}) == "YTD Return: 1.0%"
    assert ReportAgent._format_ytd_line({}) == "YTD Return: N/A%"


# ---------------------------------------------------------------------
# 3a - large-figure abbreviation for the LLM prompt
# ---------------------------------------------------------------------

def test_format_large_number_abbreviates_raw_digit_string():
    """The exact failure mode: a raw comma-grouped 12-digit revenue string
    must become an abbreviated, scale-unambiguous figure."""
    assert ReportAgent._format_large_number("466,822,987,776") == "$466.8B"
    assert ReportAgent._format_large_number(2_000_000_000) == "$2.0B"
    assert ReportAgent._format_large_number(1_500_000_000_000) == "$1.50T"


def test_format_large_number_na_and_native_currency_prefix():
    assert ReportAgent._format_large_number("N/A") == "N/A"
    assert ReportAgent._format_large_number(None) == "N/A"
    # Native (un-converted) foreign currency: no "$" (currency note discloses)
    assert ReportAgent._format_large_number(37_000_000_000_000, "") == "37.00T"


def test_money_prefix_currency_aware():
    assert ReportAgent._money_prefix({"fundamentals": {"fx_conversion": {"applied": True}}}) == "$"
    assert ReportAgent._money_prefix(
        {"fundamentals": {"fx_conversion": {"applied": False, "native_currency": "JPY"}}}
    ) == ""
    assert ReportAgent._money_prefix({"fundamentals": {}}) == "$"


# ---------------------------------------------------------------------
# 3a + 3b - integration through _prepare_context / run() with a fake client
# ---------------------------------------------------------------------

class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, sink):
        self._sink = sink

    def create(self, model, messages, **kwargs):
        # **kwargs so the test doesn't care whether the caller passes
        # max_tokens or max_completion_tokens (gpt-5.x uses the latter).
        self._sink["prompt"] = messages[0]["content"]
        self._sink["model"] = model
        self._sink["kwargs"] = kwargs
        return _FakeCompletion("GENERATED MEMO")


class _FakeChat:
    def __init__(self, sink):
        self.completions = _FakeCompletions(sink)


class _FakeOpenAI:
    """Stand-in for the OpenAI client that records the prompt it's given."""
    def __init__(self, api_key=None):
        self.sink = {}
        self.chat = _FakeChat(self.sink)


def _make_agent_with_fake_client(monkeypatch):
    fake_holder = {}

    def _factory(api_key=None):
        client = _FakeOpenAI(api_key)
        fake_holder["client"] = client
        return client

    monkeypatch.setattr(report_agent_module, "OpenAI", _factory)
    agent = ReportAgent()
    return agent, fake_holder


def _sample_outputs():
    return {
        "company_info": {"company_name": "BigCo", "sector": "Technology", "industry": "Software"},
        "market_data": {"metrics": {"latest_price": 100.0, "ytd_return": 12.3, "ytd_basis": "calendar_ytd", "volatility": 22.0}},
        "fundamentals_data": {"fundamentals": {
            # Every large dollar figure as a raw comma-grouped string (what
            # _format_number produces), so the abbreviation must handle them all.
            "revenue": "466,822,987,776", "net_income": "99,803,000,000",
            "total_assets": "352,755,000,000", "total_liabilities": "308,030,000,000",
            "total_equity": "44,725,000,000", "total_debt": "123,930,000,000",
            "cash": "48,304,000,000", "operating_cash_flow": "118,254,000,000",
            "free_cash_flow": "108,807,000,000",
            "pe_ratio": "30.00", "profit_margin": "21.00%",
            "debt_to_equity": "1.20x", "roe": "34.00%"}},
        "news_data": {}, "macro_data": {}, "risk_data": {}, "financing_data": {},
    }


def test_prepare_context_abbreviates_revenue_and_net_income(monkeypatch):
    agent, _ = _make_agent_with_fake_client(monkeypatch)
    context = agent._prepare_context("BIGCO", _sample_outputs())
    assert "Revenue: $466.8B" in context
    assert "Net Income: $99.8B" in context
    # The raw 12-digit string must NOT survive into the LLM context
    assert "466,822,987,776" not in context


def test_prepare_context_abbreviates_every_large_dollar_field(monkeypatch):
    """Item 1: the abbreviation must cover the full balance-sheet/cash-flow
    set, not just Revenue/Net Income. Assert each field is abbreviated AND
    that no raw comma-grouped digit string survives anywhere in the context."""
    agent, _ = _make_agent_with_fake_client(monkeypatch)
    context = agent._prepare_context("BIGCO", _sample_outputs())

    assert "Total Assets: $352.8B" in context
    assert "Total Liabilities: $308.0B" in context
    assert "Total Equity: $44.7B" in context
    assert "Total Debt: $123.9B" in context
    assert "Cash: $48.3B" in context
    assert "Operating Cash Flow: $118.3B" in context
    assert "Free Cash Flow: $108.8B" in context

    # The strongest guard: NO comma-grouped digit run (e.g. "466,822,987,776")
    # survives into the final context, for any field.
    assert re.search(r"\d{1,3}(?:,\d{3})+", context) is None


def test_prepare_context_large_dollar_fields_respect_native_currency(monkeypatch):
    """Foreign issuer with no FX rate: the abbreviated figures must carry no
    "$" (the currency note discloses the native currency instead), so the new
    fields compose with the FX prefix exactly as Revenue/Net Income already do."""
    agent, _ = _make_agent_with_fake_client(monkeypatch)
    outputs = _sample_outputs()
    outputs["fundamentals_data"]["fundamentals"]["fx_conversion"] = {
        "applied": False, "native_currency": "JPY"
    }
    context = agent._prepare_context("BIGCO", outputs)
    # Native-currency: abbreviated magnitude, no "$" prefix on the dollar fields.
    assert "Total Assets: 352.8B" in context
    assert "Total Assets: $352.8B" not in context


def test_run_audit_logs_full_context_matching_prompt_sent(monkeypatch, caplog):
    """3b: the exact context handed to the model is logged (ticker +
    timestamp), and that logged context is what actually reaches the client."""
    agent, holder = _make_agent_with_fake_client(monkeypatch)

    with caplog.at_level(logging.DEBUG, logger="agents.report_agent.audit"):
        result = agent.run("BIGCO", _sample_outputs())

    assert result["success"] is True

    audit_records = [r for r in caplog.records if r.name == "agents.report_agent.audit"]
    assert len(audit_records) == 1
    logged = audit_records[0].getMessage()
    assert "ticker=BIGCO" in logged
    assert "timestamp=" in logged

    # The abbreviated figures appear in the logged context AND in the prompt
    # the (fake) client actually received - i.e. the audit log faithfully
    # records what was sent, not some other string.
    prompt_sent = holder["client"].sink["prompt"]
    assert "Revenue: $466.8B" in logged
    assert "Revenue: $466.8B" in prompt_sent
