"""Planner contracts use mocked models, never provider calls."""

from unittest.mock import Mock

import pytest

from api import main


def test_old_uncapped_behavior_and_explicit_cap():
    tools = ["anomalies_sales", "top_products", "monthly_revenue", "revenue_by_segment"]
    text = ", ".join(tools)
    assert main.parse_planned_tools(text, max_tools=None) == tools
    assert main.parse_planned_tools(text, max_tools=3) == tools[:3]


def test_filtering_and_dedupe_happen_before_cap():
    text = "drop_table, top_products, top_products, monthly_revenue, invented, anomalies_sales, revenue_by_segment"
    assert main.parse_planned_tools("drop_table, top_products") == ["top_products"]
    assert main.parse_planned_tools(text, max_tools=3) == [
        "top_products", "monthly_revenue", "anomalies_sales"
    ]


@pytest.mark.parametrize("question,expected", [
    ("SEGMENT comparison", "revenue_by_segment"),
    ("product ranking", "top_products"),
    ("anomalous sales", "anomalies_sales"),
    ("anything else", "monthly_revenue"),
])
def test_keyword_fallback_and_empty_parse(monkeypatch, question, expected):
    assert main.keyword_fallback(question) == [expected]
    client = Mock()
    client.generate_content.return_value.text = "garbage, invented_tool"
    monkeypatch.setattr(main, "get_model", lambda: client)
    assert main.planner_node(main.AgentState(question)).selected_tools == [expected]


def test_exception_still_defaults_to_monthly_even_for_segment_question(monkeypatch):
    client = Mock()
    client.generate_content.side_effect = RuntimeError("synthetic failure")
    monkeypatch.setattr(main, "get_model", lambda: client)
    state = main.planner_node(main.AgentState("segment and product"))
    assert state.selected_tools == ["monthly_revenue"]


def test_planner_caps_and_tool_node_executes_only_allowlisted_names(monkeypatch):
    client = Mock()
    client.generate_content.return_value.text = "drop_table," + ",".join(main.TOOLS)
    monkeypatch.setattr(main, "get_model", lambda: client)
    state = main.planner_node(main.AgentState("test"))
    assert state.selected_tools == list(main.TOOLS)[:3]
    functions = {name: Mock(return_value=[]) for name in main.TOOLS}
    monkeypatch.setattr(main, "TOOLS", functions)
    main.tool_node(state)
    assert set(state.raw_data) == set(state.selected_tools)
    for name, function in functions.items():
        assert function.call_count == int(name in state.selected_tools)
    for function in functions.values():
        function.reset_mock()
    with pytest.raises(KeyError):
        main.tool_node(main.AgentState("test", selected_tools=["drop_table"]))
    assert not any(function.called for function in functions.values())
