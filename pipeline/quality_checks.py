"""Source-table quality checks for the incremental ecommerce orders table.

These checks run before dbt so basic ingestion problems are visible close to
the source: missing identifiers, duplicate orders, row counts, and recency.
"""

import duckdb
import os

from logger_config import logger

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("DEMO_DB_PATH", BASE_DIR / "ecommerce_project" / "dev.duckdb"))


class DataQualityError(RuntimeError):
    """Source orders failed a required ingestion quality gate."""

def main():
    """Log source quality signals and fail when order integrity is broken."""

    con = None
    
    try:   

        con = duckdb.connect(str(DB_PATH))
        
        logger.info("Connected to DuckDB")

        # Required identifier check: every order needs a stable primary key.
        nulls = con.execute("""
        SELECT COUNT(*)
        FROM incremental_orders
        WHERE order_id IS NULL
        """).fetchone()[0]

        logger.info(f"Null order IDs: {nulls}")

        # Duplicate check: duplicate order IDs would inflate all revenue marts.
        dupes = con.execute("""
        SELECT order_id, COUNT(*)
        FROM incremental_orders
        GROUP BY order_id
        HAVING COUNT(*) > 1
        """).fetchdf()

        if dupes.empty:

            logger.info("No duplicate orders found")

        else:

            logger.warning("Duplicate orders detected")
            print(dupes)
        
        # Row count and max order date provide quick operational observability.
        total_rows = con.execute("""
        SELECT COUNT(*)
        FROM incremental_orders
        """).fetchone()[0]
        
        logger.info(f"Total rows in incremental_orders: {total_rows}")

        latest_order = con.execute("""
        SELECT MAX(order_date)
        FROM incremental_orders
        """).fetchone()[0]

        logger.info(f"Latest order date: {latest_order}")    
        
        logger.info("Quality checks complete")

        failures = []
        if nulls > 0:
            failures.append(f"Null order IDs: {nulls}")
        if not dupes.empty:
            failures.append(f"Duplicate order IDs: {len(dupes)}")
        if total_rows == 0:
            failures.append("incremental_orders is empty")
        if failures:
            raise DataQualityError("; ".join(failures))
    
    finally:
        if con:
            con.close()


if __name__ == "__main__":
    main()
