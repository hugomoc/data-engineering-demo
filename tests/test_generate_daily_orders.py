"""Daily generation uses only synthetic CSV inputs and a temporary directory."""

import os
from pathlib import Path
import subprocess
import sys

import pandas as pd


def test_daily_orders_are_valid_and_do_not_overwrite(tmp_path):
    pd.DataFrame({"customer_id": ["c1", "c2"]}).to_csv(tmp_path / "customers.csv", index=False)
    pd.DataFrame({"product_id": ["p1", "p2"]}).to_csv(tmp_path / "products.csv", index=False)
    script = Path(__file__).resolve().parents[1] / "pipeline/generate_daily_orders.py"
    environment = dict(os.environ, DEMO_DATA_DIR=str(tmp_path))
    all_ids = set()
    for _ in range(2):
        subprocess.run([sys.executable, str(script)], env=environment, check=True)
    files = sorted((tmp_path / "daily_orders").glob("*.csv"))
    assert len(files) == 2
    assert files[1].stem == files[0].stem + "_1"
    for path in files:
        rows = pd.read_csv(path)
        assert len(rows) == 50
        assert rows.order_id.nunique() == 50
        assert set(rows.customer_id) <= {"c1", "c2"}
        assert set(rows.product_id) <= {"p1", "p2"}
        assert not all_ids.intersection(rows.order_id)
        all_ids.update(rows.order_id)
