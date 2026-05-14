import duckdb

con = duckdb.connect("data.db")

# Load CSV into tables
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