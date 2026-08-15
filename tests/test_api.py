"""
Tests for the public API surface: per-IP rate limiting, the global daily memo
cap, input validation, CORS lockdown, and production error sanitization. The
agent pipeline is fully mocked so no network/LLM call runs; each test uses a
distinct X-Forwarded-For so slowapi's per-IP buckets don't collide.
"""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import api


class _FakeAgent:
    def __init__(self, result):
        self._result = result

    def run(self, *args, **kwargs):
        return self._result

    def get_company_info(self, *args, **kwargs):
        return self._result


@pytest.fixture
def mock_pipeline(monkeypatch):
    """Replace every agent with a fast fake returning a minimal valid shape,
    and reset the daily-quota counter for isolation."""
    monkeypatch.setattr(api, "YFinanceClient",
                        lambda: _FakeAgent({"success": True, "company_name": "Test Co", "sector": "Technology"}))
    monkeypatch.setattr(api, "MarketDataAgent",
                        lambda: _FakeAgent({"success": True, "metrics": {}, "data": None}))
    for name in ("FinancialsAgent", "FinancingRiskAgent", "NewsAgent", "MacroAgent",
                 "PeerComparisonAgent", "RiskAgent", "ReportAgent"):
        monkeypatch.setattr(api, name, lambda: _FakeAgent({"success": True}))
    api._daily_quota["date"] = None  # reset the global cap between tests
    return api


def _client():
    return TestClient(api.app)


def test_health_is_not_rate_limited():
    # Health check is what Railway/monitoring hits; it must never 429.
    r = _client().get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_analyze_under_limit_succeeds(mock_pipeline, monkeypatch):
    monkeypatch.setenv("ANALYZE_RATE_LIMIT", "5/minute")
    r = _client().post("/api/analyze", json={"ticker": "AAPL"}, headers={"X-Forwarded-For": "10.0.0.1"})
    assert r.status_code == 200
    assert r.json()["ticker"] == "AAPL"


def test_analyze_per_ip_rate_limited(mock_pipeline, monkeypatch):
    """Over the per-IP limit returns a clear 429, not a silent failure."""
    monkeypatch.setenv("ANALYZE_RATE_LIMIT", "2/minute")
    client = _client()
    headers = {"X-Forwarded-For": "10.0.0.2"}
    codes = [client.post("/api/analyze", json={"ticker": "AAPL"}, headers=headers).status_code
             for _ in range(3)]
    assert codes == [200, 200, 429]
    blocked = client.post("/api/analyze", json={"ticker": "AAPL"}, headers=headers)
    assert blocked.status_code == 429
    assert "rate limit" in str(blocked.json()).lower()


def test_rate_limit_ignores_spoofed_forwarded_for_prefix(mock_pipeline, monkeypatch):
    """A client rotating the leftmost X-Forwarded-For value must NOT get a
    fresh bucket per request - the key is the proxy-appended (rightmost) entry.
    Without this, per-IP limiting is decorative."""
    monkeypatch.setenv("ANALYZE_RATE_LIMIT", "2/minute")
    monkeypatch.setattr(api, "TRUSTED_PROXY_COUNT", 1)
    client = _client()
    codes = [
        client.post("/api/analyze", json={"ticker": "AAPL"},
                    headers={"X-Forwarded-For": f"{i}.{i}.{i}.{i}, 5.6.7.8"}).status_code
        for i in range(3)
    ]
    assert codes == [200, 200, 429]  # spoofed prefix rotated, real IP 5.6.7.8 fixed -> capped


def test_distinct_real_origins_get_distinct_buckets(mock_pipeline, monkeypatch):
    """The fix must not swing the other way and key everyone to one bucket:
    different real (rightmost) IPs are limited independently."""
    monkeypatch.setenv("ANALYZE_RATE_LIMIT", "1/minute")
    monkeypatch.setattr(api, "TRUSTED_PROXY_COUNT", 1)
    client = _client()
    r1 = client.post("/api/analyze", json={"ticker": "AAPL"},
                     headers={"X-Forwarded-For": "1.1.1.1, 8.8.8.1"})
    r2 = client.post("/api/analyze", json={"ticker": "AAPL"},
                     headers={"X-Forwarded-For": "1.1.1.1, 8.8.8.2"})
    assert r1.status_code == 200 and r2.status_code == 200  # separate buckets


def test_global_daily_cap_blocks_beyond_limit(mock_pipeline, monkeypatch):
    """Second layer: even from fresh IPs, the global daily cap stops paid
    memo generation once the day's budget is spent."""
    monkeypatch.setenv("ANALYZE_RATE_LIMIT", "100/minute")  # don't let per-IP interfere
    monkeypatch.setattr(api, "MEMO_DAILY_CAP", 2)
    api._daily_quota["date"] = None
    client = _client()
    # different IPs each time - only the global cap should stop the third
    codes = [client.post("/api/analyze", json={"ticker": "AAPL"},
                         headers={"X-Forwarded-For": f"10.1.0.{i}"}).status_code
             for i in range(3)]
    assert codes == [200, 200, 429]


def test_daily_cap_survives_restart_via_state_file(tmp_path, monkeypatch):
    """With a state file configured, the counter reloads from disk after a
    process restart instead of resetting - so '200/day' isn't '200 since
    last restart'."""
    monkeypatch.setattr(api, "DAILY_CAP_STATE_FILE", str(tmp_path / "quota.json"))
    monkeypatch.setattr(api, "MEMO_DAILY_CAP", 2)
    monkeypatch.setattr(api, "_daily_quota", {"date": None, "count": 0})

    assert api._consume_daily_quota() is True          # count -> 1 (persisted)
    api._daily_quota = {"date": None, "count": 0}       # simulate process restart
    assert api._consume_daily_quota() is True           # reloads 1 from disk -> 2 (cap)
    api._daily_quota = {"date": None, "count": 0}
    assert api._consume_daily_quota() is False           # cap reached, read from disk
    assert json.loads((tmp_path / "quota.json").read_text())["count"] == 2


def test_daily_cap_resets_on_utc_day_boundary(tmp_path, monkeypatch):
    """A persisted count from a previous UTC day must not carry over."""
    state_file = tmp_path / "quota.json"
    state_file.write_text(json.dumps({"date": "2020-01-01", "count": 999}))
    monkeypatch.setattr(api, "DAILY_CAP_STATE_FILE", str(state_file))
    monkeypatch.setattr(api, "MEMO_DAILY_CAP", 5)
    monkeypatch.setattr(api, "_daily_quota", {"date": None, "count": 0})

    assert api._consume_daily_quota() is True  # stale date -> reset to 0 -> allowed
    assert json.loads(state_file.read_text())["count"] == 1


def test_malformed_ticker_rejected_before_any_external_call(mock_pipeline):
    for bad in ("123XYZ", "AAP L", "TOOLONGTICKER", "'; DROP", ""):
        r = _client().post("/api/analyze", json={"ticker": bad},
                           headers={"X-Forwarded-For": "10.2.0.1"})
        assert r.status_code == 422, bad


def test_hyphenated_ticker_accepted_by_api(mock_pipeline, monkeypatch):
    """A hyphenated security (preferred/warrant/unit) must reach the pipeline,
    not be rejected 422 by the validation layer."""
    monkeypatch.setenv("ANALYZE_RATE_LIMIT", "100/minute")
    r = _client().post("/api/analyze", json={"ticker": "BEP-PA"},
                       headers={"X-Forwarded-For": "10.2.0.9"})
    assert r.status_code == 200
    assert r.json()["ticker"] == "BEP-PA"


def test_cors_is_not_a_wildcard_and_rejects_unlisted_origin():
    r = _client().options(
        "/api/analyze",
        headers={"Origin": "http://evil.example.com", "Access-Control-Request-Method": "POST"},
    )
    allow = r.headers.get("access-control-allow-origin")
    assert allow != "*"
    assert allow != "http://evil.example.com"


def test_cors_allows_a_configured_origin():
    r = _client().options(
        "/api/analyze",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_production_error_response_is_sanitized(mock_pipeline, monkeypatch):
    """In production, an unexpected exception must not leak its message to the
    client - only a generic error, with full detail server-side."""
    monkeypatch.setattr(api, "IS_PRODUCTION", True)
    monkeypatch.setenv("ANALYZE_RATE_LIMIT", "100/minute")

    def boom():
        raise RuntimeError("SECRET internal detail: /path/to/thing")

    monkeypatch.setattr(api, "ReportAgent", lambda: _FakeAgentRaising(boom))
    r = _client().post("/api/analyze", json={"ticker": "AAPL"}, headers={"X-Forwarded-For": "10.3.0.1"})
    assert r.status_code == 500
    body = str(r.json())
    assert "SECRET internal detail" not in body
    assert "internal error" in body.lower()


class _FakeAgentRaising:
    def __init__(self, boom):
        self._boom = boom

    def run(self, *args, **kwargs):
        self._boom()
