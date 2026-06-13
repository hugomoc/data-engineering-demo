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
TRACKING_FILE = BASE_DIR / "data" / "processed_files.txt"


def main():

    con = duckdb.connect(str(DB_PATH))
    
    try:    

        logger.info("CUSTOMERS_FILE: %s", CUSTOMERS_FILE)
        logger.info("PRODUCTS_FILE: %s", PRODUCTS_FILE)
        logger.info("DAILY_FOLDER: %s", DAILY_FOLDER)
        logger.info("DB_PATH: %s", DB_PATH)
      
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
        

        if TRACKING_FILE.exists():
            with open(TRACKING_FILE, "r") as f:
                processed_files = set(f.read().splitlines())

        else:
            processed_files = set()

        logger.info("Previously processed files: %s",
        len(processed_files)
)

        
        #Process new files
        

        new_files_processed = 0

        for filename in os.listdir(DAILY_FOLDER):

            if filename.endswith(".csv") and filename not in processed_files:

                file_path = os.path.join(DAILY_FOLDER, filename)

                logger.info(f"Processing file: {filename}")

                df = pd.read_csv(file_path)
                df["order_id"] = df["order_id"].astype(str)

                con.register("temp_df", df)

                rows_before = con.execute("SELECT COUNT(*) FROM incremental_orders"
                ).fetchone()[0]            
                
                temp_rows = con.execute("SELECT COUNT(*) FROM temp_df"
                ).fetchone()[0]
                
                total_rows = con.execute("SELECT COUNT(*) FROM incremental_orders"
                ).fetchone()[0]
                

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
                        CAST(order_id AS VARCHAR),
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
                        WHERE i.order_id = CAST(t.order_id AS VARCHAR)
                    )
                """)
                
                con.unregister("temp_df")
                
                result = con.execute("SELECT COUNT(*) FROM incremental_orders"
                ).fetchone()

                logger.info("Rows in temp_df: %s", temp_rows)
                
                logger.info("Total rows in incremental_orders: %s", total_rows)

                rows_after = con.execute("SELECT COUNT(*) FROM incremental_orders"
                ).fetchone()[0]

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


    finally:
        con.close()
        logger.info("DuckDB connection closed")


if __name__ == "__main__":
    main()