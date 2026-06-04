import duckdb
import os
import pandas as pd

from logger_config import logger

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

CUSTOMERS_FILE = BASE_DIR / "data" / "customers.csv"
PRODUCTS_FILE = BASE_DIR / "data" / "products.csv"
DAILY_FOLDER = BASE_DIR / "data" / "daily_orders"

DB_PATH = BASE_DIR / "ecommerce_project" / "dev.duckdb"
TRACKING_FILE = "processed_files.txt"


def main():

    con = duckdb.connect(str(DB_PATH))

    logger.info("Connected to DuckDB")
    print("CUSTOMERS_FILE =", CUSTOMERS_FILE)
    print("PRODUCTS_FILE =", PRODUCTS_FILE)
    print("DAILY_FOLDER =", DAILY_FOLDER)
    print("DB_PATH =", DB_PATH)

  
    #Load dimension tables
   

    con.execute(f"""
    CREATE OR REPLACE TABLE customers AS
    SELECT *
    FROM read_csv_auto('{CUSTOMERS_FILE}')
    """)

    logger.info("Customers loaded")

    con.execute(f"""
    CREATE OR REPLACE TABLE products AS
    SELECT *
    FROM read_csv_auto('{PRODUCTS_FILE}')
    """)

    logger.info("Products loaded")

    
    #Create incremental fact table
   

    con.execute("""
    CREATE TABLE IF NOT EXISTS incremental_orders (
        order_id VARCHAR,
        customer_id INTEGER,
        product_id INTEGER,
        unit_price DOUBLE,
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
            
            print(con.execute("SELECT COUNT(*) FROM temp_df").fetchone())

            con.execute("""
                INSERT INTO incremental_orders (
                    order_id,
                    customer_id,
                    product_id,
                    unit_price,
                    quantity,
                    amount,
                    order_date,
                    created_at
                )
                SELECT
                    order_id,
                    customer_id,
                    product_id,
                    amount / NULLIF(quantity, 0) AS unit_price,
                    quantity,
                    amount,
                    order_date,
                    CURRENT_TIMESTAMP
                FROM temp_df t
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM incremental_orders i
                    WHERE i.order_id = t.order_id
                )
            """)
            
            result = con.execute("""
            SELECT COUNT(*) 
            FROM incremental_orders
            """).fetchone()

            print(result)

            rows_after = con.execute("""
            SELECT COUNT(*)
            FROM incremental_orders
            """).fetchone()[0]

            inserted_rows = rows_after - rows_before

            if inserted_rows == 0:
                logger.info(
                    "No rows inserted | file=%s | reason=already_loaded_or_duplicate_data",
                    filename
                )
            else:
                logger.info(
                    "Insert summary | file=%s | inserted_rows=%s",
                    filename,
                    inserted_rows
                )

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