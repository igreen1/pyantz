"""Create sample CSV files needed by the data analysis example."""

from __future__ import annotations

import polars as pl

data_dir = "/tmp/pyantz_data"

pl.DataFrame(
    {
        "order_id": [1, 2, 3, 4, 5],
        "product_id": [101, 102, 101, 103, 102],
        "quantity": [2, 1, 5, 3, 2],
    }
).write_csv(f"{data_dir}/sales.csv")

pl.DataFrame(
    {
        "product_id": [101, 102, 103],
        "name": ["Widget", "Gadget", "Doohickey"],
        "price": [9.99, 24.99, 4.99],
    }
).write_csv(f"{data_dir}/products.csv")

print(f"Sample data written to {data_dir}/")
