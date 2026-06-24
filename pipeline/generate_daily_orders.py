import pandas as pd
import random
from datetime import datetime
from pathlib import Path
import uuid

# -----------------------------
# Config
# -----------------------------

BASE_DIR = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path.cwd()

DATA_DIR = BASE_DIR / "data"

CUSTOMERS_PATH = DATA_DIR / "customers.csv"
PRODUCTS_PATH = DATA_DIR / "products.csv"
DAILY_FOLDER = DATA_DIR / "daily_orders"

DAILY_FOLDER.mkdir(parents=True, exist_ok=True)

valid_customers = pd.read_csv(CUSTOMERS_PATH)
products_df = pd.read_csv(PRODUCTS_PATH)
products = products_df["product_id"].tolist()

NUM_ORDERS = 50

# -----------------------------
# Generate Orders
# -----------------------------

rows = []

for _ in range(NUM_ORDERS):

    quantity = random.randint(1, 5)
    price = random.randint(20, 500)

    order = {
        "order_id": str(uuid.uuid4()),
        "customer_id": random.choice(customer_ids),
        "product_id": random.choice(products),
        "quantity": quantity,
        "unit_price": price,
        "amount": quantity * price,
        "order_date": today,
        "created_at": datetime.now().isoformat()
    }

    rows.append(order)

# -----------------------------
# Save CSV
# -----------------------------

df = pd.DataFrame(rows)

df.to_csv(filename, index=False)

print(f"Generated {len(df)} orders")
print(f"Saved to: {filename}")