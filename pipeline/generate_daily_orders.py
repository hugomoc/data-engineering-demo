import pandas as pd
import random
from datetime import datetime
from pathlib import Path
import uuid

# -----------------------------
# Config
# -----------------------------

DAILY_FOLDER = Path("data/daily_orders")
DAILY_FOLDER.mkdir(parents=True, exist_ok=True)

today = datetime.now().strftime("%Y-%m-%d")

filename = DAILY_FOLDER / f"{today}.csv"

products = [101, 102, 103, 104, 105]

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
        "customer_id": random.randint(1, 50),
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