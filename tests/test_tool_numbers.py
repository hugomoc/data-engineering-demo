"""Compare actual API tools/metrics with independent source/fact SQL."""

import importlib

import duckdb
import pytest

from eval.fixture import build_database, find_dbt


@pytest.fixture(scope="module")
def tool_database(tmp_path_factory):
    if not find_dbt():
        pytest.skip("dbt is unavailable; install dbt-duckdb to run numeric tool checks")
    return build_database(tmp_path_factory.mktemp("agent-tool-numbers"))


@pytest.fixture
def tool_state(tool_database, monkeypatch):
    from api import main
    previous = main.DB_PATH
    monkeypatch.setenv("DEMO_DB_PATH", str(tool_database))
    importlib.reload(main)
    assert main.DB_PATH == tool_database
    try:
        state = main.AgentState("synthetic numeric check", selected_tools=list(main.TOOLS))
        yield main.compute_node(main.tool_node(state))
    finally:
        main.DB_PATH = previous


def test_top_product_revenue_and_shares(tool_database, tool_state):
    with duckdb.connect(str(tool_database), read_only=True) as connection:
        expected = connection.execute("""
            SELECT p.product_name, sum(o.amount), sum(o.quantity),
                   100.0 * sum(o.amount) / sum(sum(o.amount)) OVER ()
            FROM stg_orders o JOIN stg_products p USING (product_id)
            GROUP BY p.product_name
        """).fetchall()
    raw = {row["product_name"]: row for row in tool_state.raw_data["top_products"]}
    shares = {row["product"]: row["share"] for row in tool_state.computed_data["product_contribution"]}
    assert set(raw) == {row[0] for row in expected} == set(shares)
    for name, revenue, quantity, share in expected:
        assert raw[name]["revenue"] == pytest.approx(revenue)
        assert raw[name]["units_sold"] == quantity
        assert shares[name] == pytest.approx(share)


def test_segment_revenue_and_shares(tool_database, tool_state):
    with duckdb.connect(str(tool_database), read_only=True) as connection:
        expected = connection.execute("""
            SELECT segment, sum(amount), 100.0 * sum(amount) / sum(sum(amount)) OVER ()
            FROM fct_sales GROUP BY segment
        """).fetchall()
    raw = {row["segment"]: row["revenue"] for row in tool_state.raw_data["revenue_by_segment"]}
    shares = {row["segment"]: row["share"] for row in tool_state.computed_data["segment_contribution"]}
    assert set(raw) == {row[0] for row in expected} == set(shares)
    assert sum(shares.values()) == pytest.approx(100)
    for name, revenue, share in expected:
        assert raw[name] == pytest.approx(revenue)
        assert shares[name] == pytest.approx(share)


def test_monthly_revenue_and_latest_delta(tool_database, tool_state):
    with duckdb.connect(str(tool_database), read_only=True) as connection:
        expected = connection.execute("""
            SELECT strftime(order_date, '%Y-%m') AS month, sum(amount) AS revenue
            FROM stg_orders GROUP BY 1 ORDER BY 1
        """).fetchall()
    actual = sorted((r["month"], r["revenue"]) for r in tool_state.raw_data["monthly_revenue"])
    assert len(actual) == len(expected) == 3
    for row, oracle in zip(actual, expected):
        assert row[0] == oracle[0]
        assert row[1] == pytest.approx(oracle[1])
    delta = tool_state.computed_data["revenue_delta"]
    previous, current = expected[-2:]
    assert delta["previous_month"] == dict(month=previous[0], revenue=previous[1])
    assert delta["current_month"] == dict(month=current[0], revenue=current[1])
    assert delta["absolute_change"] == pytest.approx(current[1] - previous[1])
    assert delta["percent_change"] == pytest.approx(100 * (current[1] - previous[1]) / previous[1])


def test_anomaly_months_against_sql_threshold(tool_database, tool_state):
    with duckdb.connect(str(tool_database), read_only=True) as connection:
        expected = connection.execute("""
            WITH monthly AS (
                SELECT strftime(order_date, '%Y-%m') AS month, sum(amount) AS revenue
                FROM fct_sales GROUP BY 1
            )
            SELECT month, revenue FROM monthly
            WHERE revenue < 0.8 * (SELECT avg(revenue) FROM monthly)
            ORDER BY month
        """).fetchall()
    actual = sorted(tool_state.raw_data["anomalies_sales"], key=lambda r: r["month"])
    assert tool_state.computed_data["anomalies_sales"] == actual
    assert len(actual) == len(expected)
    for row, oracle in zip(actual, expected):
        assert row["month"] == oracle[0]
        assert row["revenue"] == pytest.approx(oracle[1])
        assert row["reason"] == "Below expected range"
