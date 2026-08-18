"""Legacy SQL runner for materializing analytics tables outside dbt.

The active analytics layer lives in dbt, but this script documents the earlier
pattern: read SQL files, create DuckDB tables, and preview the results.
"""

import duckdb

from logger_config import logger
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SQL_DIR = BASE_DIR / "sql"
DB_PATH = BASE_DIR / "ecommerce_project" / "dev.duckdb"

queries = {
    "top_products": SQL_DIR / "top_products.sql",
    "revenue_by_segment": SQL_DIR /"revenue_by_segment.sql",
    "monthly_revenue": SQL_DIR /"monthly_revenue.sql"
}


def main():
    """Execute each SQL file and replace its matching DuckDB table."""

    con = duckdb.connect(str(DB_PATH))

    logger.info("Connected to DuckDB")

    # -----------------------------
    # Run SQL transformations
    # -----------------------------

    for table_name, path in queries.items():

        logger.info(f"Running query: {table_name}")
        print(f"Opening: {path}")
        with open(path, "r") as file:
            query = file.read()

        # Materialize the query result into a table named after the SQL file key.
        con.execute(f"""
            CREATE OR REPLACE TABLE {table_name} AS
            {query}
        """)

        logger.info(f"Created table: {table_name}")

        # Print a tiny preview so manual runs can verify the transformation.
        preview = con.execute(f"""
            SELECT *
            FROM {table_name}
            LIMIT 5
        """).fetchdf()

        print(f"\n--- {table_name} preview ---")
        print(preview)

    logger.info("All transformations completed")


if __name__ == "__main__":
    main()
