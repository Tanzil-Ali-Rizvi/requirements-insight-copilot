"""Read-only, sandboxed DuckDB connection over the star schema.

Tables are loaded into memory from Parquet, then file and network access is switched off and
the configuration is locked, so a query the copilot runs cannot read other files, write, or
reach the network even if it slipped past the SQL guard.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE = ROOT / "data" / "warehouse"
TABLES = ("dim_customer", "dim_seller", "dim_product", "fct_order_items", "fct_orders")

SCHEMA_DOC = """\
fct_orders (one row per order, 99,441 rows; delivery measures are NULL unless delivered)
  order_id, customer_id, seller_id (first item's seller), order_status,
  purchase_ts, purchase_date, purchase_month (DATE, first of month), approved_ts,
  carrier_ts (handed to carrier), delivered_ts, estimated_date (promised date),
  shipping_limit_ts (seller's handoff deadline), n_items, n_sellers, items_value, freight_value,
  payment_value (BRL), review_score (1-5), customer_state, customer_region, seller_state,
  seller_region, same_state (BOOL), is_delivered (BOOL), is_late (BOOL, delivered after the
  promised date), days_vs_estimate (negative = early), promised_days, total_days,
  days_to_carrier, transit_days, seller_handoff_late (BOOL, carrier_ts > shipping_limit_ts)
fct_order_items (one row per item): order_id, order_item_id, product_id, seller_id,
  shipping_limit_ts, price, freight_value
dim_customer: customer_id, customer_unique_id, city, state, region
dim_seller: seller_id, city, state, region
dim_product: product_id, category (English), weight_g
Regions: North, Northeast, Center-West, Southeast, South. Always filter is_delivered for delivery KPIs.
"""


def _build(warehouse: Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database=":memory:")
    for table in TABLES:
        path = (warehouse / f"{table}.parquet").as_posix()
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_parquet('{path}')")
    con.execute("SET enable_external_access = false")
    con.execute("SET lock_configuration = true")
    return con


@lru_cache(maxsize=1)
def connection() -> duckdb.DuckDBPyConnection:
    """Shared sandboxed connection (built once per process)."""
    return _build(WAREHOUSE)


def query(sql: str) -> pd.DataFrame:
    """Run SQL that has already passed the guard. Uses a cursor so callers are thread-safe."""
    return connection().cursor().execute(sql).df()
