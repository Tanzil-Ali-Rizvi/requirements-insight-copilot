"""Build the star schema from the raw CSVs and export it as Parquet.

The Parquet files in data/warehouse/ are committed, so the app, tests and evals run
without downloading anything. Re-run this after `python scripts/fetch_data.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "warehouse"
TABLES = ["dim_customer", "dim_seller", "dim_product", "fct_order_items", "fct_orders"]


def main() -> int:
    if not (RAW / "olist_orders_dataset.csv").exists():
        print("Raw data missing: run `python scripts/fetch_data.py` first.")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    for script in ("01_staging.sql", "02_star_schema.sql"):
        sql = (ROOT / "sql" / script).read_text().replace("{raw}", RAW.as_posix())
        con.execute(sql)
    for table in TABLES:
        target = OUT / f"{table}.parquet"
        con.execute(f"COPY {table} TO '{target.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<16} {n:>9,} rows  {target.stat().st_size / 1e6:5.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
