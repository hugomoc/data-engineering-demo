import duckdb
import os
import pandas as pd

from logger_config import logger

DB_PATH = "../data.db"
DAILY_FOLDER = "../data/daily_orders"
TRACKING_FILE = "processed_files.txt"


def main():

    con = duckdb.connect(DB_PATH)

    logger.info("Connected to DuckDB")

  
    #Load dimension tables
   

    con.execute("""
    CREATE OR REPLACE TABLE customers AS
    SELECT *
    FROM read_csv_auto('../data/customers.csv')
    """)

    logger.info("Customers loaded")

    con.execute("""
    CREATE OR REPLACE TABLE products AS
    SELECT *
    FROM read_csv_auto('../data/products.csv')
    """)

    logger.info("Products loaded")

    
    #Create incremental fact table
   

    con.execute("""
    CREATE TABLE IF NOT EXISTS incremental_orders (
        order_id INTEGER,
        customer_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        amount DOUBLE,
        order_date DATE,
        created_at TIMESTAMP
    )
    """)

    logger.info("incremental_orders table ready")

    
    #Read processed files
    

    if os.path.exists(TRACKING_FILE):

        with open(TRACKING_FILE, "r") as f:
            processed_files = set(f.read().splitlines())

    else:
        processed_files = set()

    logger.info(f"Previously processed files: {len(processed_files)}")

    
    #Process new files
    

    new_files_processed = 0

    for filename in os.listdir(DAILY_FOLDER):

        if filename.endswith(".csv") and filename not in processed_files:

            file_path = os.path.join(DAILY_FOLDER, filename)

            logger.info(f"Processing file: {filename}")

            df = pd.read_csv(file_path)

            rows_before = con.execute("""
            SELECT COUNT(*)
            FROM incremental_orders
            """).fetchone()[0]

            con.register("temp_df", df)

            con.execute("""
                INSERT INTO incremental_orders
                SELECT *
                FROM temp_df t
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM incremental_orders i
                    WHERE i.order_id = t.order_id
                )
            """)

            rows_after = con.execute("""
            SELECT COUNT(*)
            FROM incremental_orders
            """).fetchone()[0]

            inserted_rows = rows_after - rows_before

            logger.info(f"Inserted rows: {inserted_rows}")

            # Mark file as processed
            with open(TRACKING_FILE, "a") as f:
                f.write(filename + "\n")

            logger.info(f"Finished processing: {filename}")

            new_files_processed += 1

    if new_files_processed == 0:
        logger.info("No new files found")

    logger.info("Incremental load complete")


if __name__ == "__main__":
    main()