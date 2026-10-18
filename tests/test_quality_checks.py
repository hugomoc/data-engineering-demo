"""Source gate checks use disposable databases and an in-memory logger."""

import logging
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

import duckdb
import pytest


@pytest.mark.parametrize("ids,reason", [
    (["one", "two"], None),
    (["one", None], "Null order IDs"),
    (["one", "one"], "Duplicate order IDs"),
    ([], "incremental_orders is empty"),
])
def test_quality_gate(tmp_path, monkeypatch, caplog, ids, reason):
    database = tmp_path / "quality.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute("CREATE TABLE incremental_orders (order_id VARCHAR, order_date DATE)")
        if ids:
            connection.executemany(
                "INSERT INTO incremental_orders VALUES (?, '2026-01-01')",
                [(value,) for value in ids],
            )
    monkeypatch.setenv("DEMO_DB_PATH", str(database))
    monkeypatch.setitem(sys.modules, "logger_config",
                        SimpleNamespace(logger=logging.getLogger("quality-test")))
    script = Path(__file__).resolve().parents[1] / "pipeline/quality_checks.py"
    namespace = runpy.run_path(str(script))
    assert namespace["DB_PATH"] == database
    with caplog.at_level(logging.INFO):
        if reason:
            with pytest.raises(namespace["DataQualityError"], match=reason):
                namespace["main"]()
        else:
            namespace["main"]()
    assert "Null order IDs:" in caplog.text
    assert "Total rows in incremental_orders:" in caplog.text
    assert "Latest order date:" in caplog.text
    # A raised gate must still close its database connection.
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM incremental_orders").fetchone()[0] == len(ids)
