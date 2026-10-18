"""Exercise two incremental dbt builds without opening the demo database."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import duckdb
import pytest


PROJECT = Path(__file__).resolve().parents[1] / "ecommerce_project"
DBT = Path(sys.executable).parent / "dbt"


def test_incremental_fact_keeps_random_uuid_orders(tmp_path):
    executable = str(DBT) if DBT.is_file() else shutil.which("dbt")
    if not executable:
        pytest.skip("dbt is not installed; install dbt-duckdb to run incremental regression")

    database = tmp_path / "sales.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute("CREATE TABLE customers (customer_id VARCHAR, name VARCHAR, segment VARCHAR)")
        connection.execute("INSERT INTO customers VALUES ('c1', 'Synthetic customer', 'retail')")
        connection.execute("CREATE TABLE products (product_id VARCHAR, product_name VARCHAR, category VARCHAR)")
        connection.execute("INSERT INTO products VALUES ('p1', 'Synthetic product', 'demo')")
        connection.execute("""CREATE TABLE incremental_orders (
            order_id VARCHAR, customer_id VARCHAR, product_id VARCHAR,
            unit_price DOUBLE, quantity INTEGER, amount DOUBLE,
            order_date DATE, created_at TIMESTAMP)""")

    environment = os.environ.copy()
    environment.update(
        DUCKDB_PATH=str(database),
        DBT_PROFILES_DIR=str(PROJECT),
        DBT_SEND_ANONYMOUS_USAGE_STATS="false",
    )
    for batch, timestamp in enumerate(("2026-01-01 12:00:00", "2026-01-02 12:00:00")):
        with duckdb.connect(str(database)) as connection:
            connection.executemany(
                "INSERT INTO incremental_orders VALUES (?, 'c1', 'p1', 25, 2, 50, '2026-01-01', ?)",
                [(str(uuid4()), timestamp) for _ in range(30)],
            )
        result = subprocess.run(
            [executable, "build", "--project-dir", str(PROJECT),
             "--profiles-dir", str(PROJECT), "--target-path", str(tmp_path / "target"),
             "--log-path", str(tmp_path / "logs")],
            cwd=PROJECT, env=environment, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        with duckdb.connect(str(database), read_only=True) as connection:
            assert connection.execute(
                "SELECT count(*), count(DISTINCT order_id) FROM fct_sales"
            ).fetchone() == (30 * (batch + 1), 30 * (batch + 1))
