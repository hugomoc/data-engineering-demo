import duckdb

from logger_config import logger

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "ecommerce_project" / "dev.duckdb"

def main():

    con = None
    
    try:   

        con = duckdb.connect(str(DB_PATH))
        
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

        latest_order = con.execute("""
        SELECT MAX(order_date)
        FROM incremental_orders
        """).fetchone()[0]

        logger.info(f"Latest order date: {latest_order}")    
        
        logger.info("Quality checks complete")
    
    finally:
        if con:
            con.close()


if __name__ == "__main__":
    main()