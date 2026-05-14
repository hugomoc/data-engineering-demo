import duckdb

from logger_config import logger

DB_PATH = "../data.db"

def main():

    con = duckdb.connect(DB_PATH)
    
    logger.info("Connected to DuckDB")

    # Null check
    nulls = con.execute("""
    SELECT COUNT(*)
    FROM incremental_orders
    WHERE order_id IS NULL
    """).fetchone()[0]

    logger.info(f"Null order IDs: {nulls}")

    # Duplicate check
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
    
    # Total row count
    total_rows = con.execute("""
    SELECT COUNT(*)
    FROM incremental_orders
    """).fetchone()[0]

    logger.info(f"Total rows in incremental_orders: {total_rows}")

    logger.info("Quality checks complete")


if __name__ == "__main__":
    main()