"""Offline metric and API hardening regressions; no database or model calls."""

from unittest.mock import Mock, patch

import pytest

from api.metrics import (
    build_fallback_summary, compute_product_contribution,
    compute_revenue_delta, compute_segment_contribution, detect_sales_anomalies,
)


def test_revenue_delta():
    assert "error" in compute_revenue_delta([])
    assert "error" in compute_revenue_delta([{"month": "2026-01", "revenue": 100}])
    result = compute_revenue_delta([
        {"month": "2026-02", "revenue": 75}, {"month": "2026-01", "revenue": 100}
    ])
    assert result["absolute_change"] == -25
    assert result["percent_change"] == -25


def test_contribution_shares():
    products = compute_product_contribution([
        {"product_name": "A", "revenue": 30}, {"product_name": "B", "revenue": 70}
    ])
    segments = compute_segment_contribution([
        {"segment": "A", "revenue": 80}, {"segment": "B", "revenue": 20}
    ])
    assert sum(row["share"] for row in products) == pytest.approx(100)
    assert sum(row["share"] for row in segments) == pytest.approx(100)


def test_anomalies():
    assert detect_sales_anomalies([]) == []
    rows = [{"month": "2026-01", "revenue": 100}, {"month": "2026-02", "revenue": 20}]
    assert detect_sales_anomalies(rows) == [dict(rows[1], reason="Below expected range")]


@pytest.mark.parametrize("current,direction", [(75, "decreased"), (125, "increased")])
def test_fallback_revenue_direction(current, direction):
    delta = compute_revenue_delta([
        {"month": "2026-01", "revenue": 100}, {"month": "2026-02", "revenue": current}
    ])
    text = build_fallback_summary({"revenue_delta": delta})
    assert f"Revenue {direction}" in text
    assert "Top Product" not in text
    assert "Anomalies" not in text


def test_fallback_missing_metrics_and_quota_path():
    from api import main
    from google.api_core.exceptions import ResourceExhausted

    metrics = {"revenue_delta": {"error": "too little data"}, "anomalies_sales": []}
    client = Mock()
    client.generate_content.side_effect = ResourceExhausted("synthetic quota")
    state = main.AgentState("question", computed_data=metrics)
    with patch.object(main, "get_model", return_value=client):
        assert main.analyst_node(state).final_answer == build_fallback_summary(metrics)
    assert "Revenue" not in state.final_answer
    assert "0 unusual month(s)" in state.final_answer
    assert build_fallback_summary({}) == "Executive Summary"


def test_fallback_product_and_segment_sections():
    text = build_fallback_summary({
        "product_contribution": [{"product": "A", "revenue": 100, "share": 100}],
        "segment_contribution": [{"segment": "retail", "revenue": 100, "share": 100}],
    })
    assert "Top Product: A" in text
    assert "Top Customer Segment: retail" in text
    assert "Revenue increased" not in text


def test_agent_error_is_generic_and_logged(caplog):
    from api import main
    with patch.object(main, "run_agent", side_effect=RuntimeError("private failure")):
        assert main.ask("question", session_id="synthetic") == {
            "question": "question", "error": "The agent could not answer this question."
        }
    assert "Agent failed" in caplog.text


def test_key_required_only_at_agent_call(monkeypatch):
    from api import main
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(main, "model", None)
    with patch.object(main, "load_dotenv"):
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            main.run_agent("question")
