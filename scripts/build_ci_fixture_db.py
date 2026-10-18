"""Build deterministic source tables for offline dbt CI in a fresh database."""

from datetime import date, datetime, timedelta
import os
from pathlib import Path
import random
from uuid import UUID

import duckdb


REPO_ROOT = Path(__file__).resolve().parents[1]


def build_fixture(database: Path) -> None:
    database = database.expanduser().resolve()
    protected = REPO_ROOT / "ecommerce_project" / "dev.duckdb"
    if database == protected or str(database).startswith(str(protected) + "."):
        raise ValueError("The demo database cannot be used for a CI fixture")
    if database.exists():
        raise FileExistsError(f"Refusing to overwrite existing fixture: {database}")

    database.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    with duckdb.connect(str(database)) as connection:
        for table in ("customers", "products"):
            connection.execute(
                f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto(?)",
                [str(REPO_ROOT / "data" / f"{table}.csv")],
            )
        customers = [row[0] for row in connection.execute(
            "SELECT customer_id FROM customers ORDER BY customer_id").fetchall()]
        products = connection.execute(
            "SELECT product_id, price FROM products ORDER BY product_id").fetchall()
        connection.execute("""CREATE TABLE incremental_orders (
            order_id VARCHAR, customer_id INTEGER, product_id INTEGER,
            unit_price DOUBLE, quantity INTEGER, amount DOUBLE,
            order_date DATE, created_at TIMESTAMP)""")
        orders = []
        for index in range(300):
            batch = index // 100
            order_id = str(UUID(int=rng.getrandbits(128), version=4))
            customer = rng.choice(customers)
            product, price = rng.choice(products)
            quantity = rng.randint(1, 5)
            orders.append((
                order_id, customer, product, price, quantity, quantity * price,
                date(2026, batch + 1, 1) + timedelta(days=index % 28),
                datetime(2026, 1, 1) + timedelta(days=batch, seconds=index % 100),
            ))
        connection.executemany(
            "INSERT INTO incremental_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)", orders,
        )
    print("Created CI fixture with 300 orders across three calendar months")


def main() -> None:
    path = os.environ.get("DUCKDB_PATH")
    if not path:
        raise ValueError("DUCKDB_PATH must name a fresh temporary database")
    build_fixture(Path(path))


if __name__ == "__main__":
    main()
