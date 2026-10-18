"""One-time CSV bootstrap loader for the simple local DuckDB database.

LEGACY: retained for reference; use incremental_load.py for the active pipeline.

This script predates the dbt-oriented incremental flow and loads the three
base CSV files directly into data.db for quick local experimentation.
"""

import duckdb

con = duckdb.connect("data.db")

# Replace the bootstrap tables so local experiments start from the CSV state.
con.execute("""
CREATE OR REPLACE TABLE customers AS
SELECT * FROM read_csv_auto('data/customers.csv');
""")

con.execute("""
CREATE OR REPLACE TABLE products AS
SELECT * FROM read_csv_auto('data/products.csv');
""")

con.execute("""
CREATE OR REPLACE TABLE orders AS
SELECT * FROM read_csv_auto('data/orders.csv');
""")

print("Tables created successfully!")
