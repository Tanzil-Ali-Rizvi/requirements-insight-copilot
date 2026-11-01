"""Download the Olist e-commerce CSVs (MIT licence) from Olist's official GitHub repository.

Usage:  python scripts/fetch_data.py
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/"
FILES = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_order_payments_dataset.csv",
    "product_category_name_translation.csv",
]
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = RAW / name
        if target.exists():
            print(f"  exists  {name}")
            continue
        print(f"  fetch   {name}")
        urllib.request.urlretrieve(BASE + name, target)
    print(f"Raw data in {RAW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
