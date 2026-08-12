"""
Tests for MacroAgent - output shape, the consumer contract (the numeric
*_value fields risk_agent reads and the string labels report_agent/frontend
read), graceful degradation, and the macro->risk threshold wiring. All
synthetic: fred_client.get_macro_indicators is stubbed, no network.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.macro_agent import MacroAgent
from agents.risk_agent import RiskAgent

# Shape mirrors FREDClient.get_macro_indicators() live output.
CANNED = {
    "success": True,
    "data": {
        "fed_rate": "3.63%", "fed_rate_value": 3.63,
        "10y_treasury": "4.72%", "10y_treasury_value": 4.72,
        "cpi_inflation": "3.7% YoY", "cpi_inflation_value": 3.7265,
        "unemployment_rate": "4.1%", "unemployment_rate_value": 4.1,
        "vix_index": "15.46", "vix_index_value": 15.46,
    },
}


def make_agent(canned):
    """MacroAgent.__init__ makes a FREDClient (no network until a call), so we
    just replace the indicator-fetch with a stub."""
    agent = MacroAgent()
    agent.fred_client.get_macro_indicators = lambda: canned
    return agent


def test_run_returns_indicators_and_analysis():
    out = make_agent(CANNED).run(sector="Technology")
    assert out["success"] is True
    assert out["indicators"] == CANNED["data"]
    for key in ("interest_rates", "treasury_impact", "inflation_impact", "labor_market", "summary"):
        assert key in out["analysis"]
    assert "Technology" in out["analysis"]["summary"]


def test_output_carries_fields_both_consumers_read():
    """Locks the contract: risk_agent reads the numeric *_value fields, while
    report_agent and the frontend read the string labels. Both must be
    present, or a consumer silently breaks."""
    ind = make_agent(CANNED).run()["indicators"]
    for numeric in ("fed_rate_value", "cpi_inflation_value", "unemployment_rate_value"):
        assert isinstance(ind[numeric], (int, float)), numeric
    for label in ("fed_rate", "cpi_inflation", "unemployment_rate", "10y_treasury", "vix_index"):
        assert isinstance(ind[label], str), label


def test_run_fails_gracefully_when_fred_unsuccessful():
    out = make_agent({"success": False}).run()
    assert out["success"] is False


def test_analysis_reports_unavailable_for_missing_values():
    out = make_agent({"success": True, "data": {}}).run()
    assert "unavailable" in out["analysis"]["interest_rates"].lower()
    assert "unavailable" in out["analysis"]["inflation_impact"].lower()


def test_run_never_raises_on_exception():
    agent = MacroAgent()

    def boom():
        raise RuntimeError("FRED down")

    agent.fred_client.get_macro_indicators = boom
    out = agent.run()
    assert out["success"] is False
    assert "error" in out


def test_macro_output_drives_risk_agent_thresholds():
    """End-to-end contract: an elevated fed rate in macro output must trip
    risk_agent's numeric-threshold macro risk. Guards the *_value wiring that
    a string-only output would silently break."""
    high = {"success": True, "data": {**CANNED["data"], "fed_rate": "5.50%", "fed_rate_value": 5.5}}
    macro = make_agent(high).run(sector="Technology")
    analysis = {
        "market_data": {}, "fundamentals_data": {}, "news_data": {},
        "company_info": {"sector": "Technology", "company_name": "X"},
        "macro_data": macro, "financing_data": {},
    }
    titles = [r["title"] for r in RiskAgent().run("X", analysis)["risks"]]
    assert "Interest Rate Vulnerability" in titles  # fed_rate_value 5.5 >= 5.0 -> High
