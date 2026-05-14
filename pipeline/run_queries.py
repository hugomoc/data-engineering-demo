import duckdb

from logger_config import logger

DB_PATH = "../data.db"

queries = {
    "top_products": "../sql/top_products.sql",
    "revenue_by_segment": "../sql/revenue_by_segment.sql",
    "monthly_revenue": "../sql/monthly_revenue.sql"
}


def main():

    con = duckdb.connect(DB_PATH)

    logger.info("Connected to DuckDB")

    # -----------------------------
    # Run SQL transformations
    # -----------------------------

    for table_name, path in queries.items():

        logger.info(f"Running query: {table_name}")

        with open(path, "r") as file:
            query = file.read()

        # Create analytics table
        con.execute(f"""
            CREATE OR REPLACE TABLE {table_name} AS
            {query}
        """)

        logger.info(f"Created table: {table_name}")

        # Preview results
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