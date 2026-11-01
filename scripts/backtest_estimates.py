"""Backtest a route- and load-aware delivery estimate against Olist's actual promised dates.

Train: orders purchased before 2018-01-01. Test: orders purchased Jan-Aug 2018.
Estimate = percentile p of delivery time on the seller-state -> customer-state route (>= 30 orders,
else the customer state, else national), scaled up by a load factor: the median delivery time of
orders delivered in the 14 days before the purchase, relative to the training median. Only data
known at purchase time is used.

Writes reports/backtest.json and prints a table of late rate vs average promised days.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
FCT = (ROOT / "data" / "warehouse" / "fct_orders.parquet").as_posix()
PERCENTILES = (0.85, 0.88, 0.90, 0.92, 0.95)

SQL = """
WITH train AS (SELECT * FROM f WHERE is_delivered AND purchase_ts <  TIMESTAMP '2018-01-01'),
test  AS (SELECT * FROM f WHERE is_delivered AND purchase_ts >= TIMESTAMP '2018-01-01'),
route AS (SELECT seller_state, customer_state, COUNT(*) AS n, QUANTILE_CONT(total_days, {p}) AS q
          FROM train GROUP BY 1, 2),
cst   AS (SELECT customer_state, QUANTILE_CONT(total_days, {p}) AS q FROM train GROUP BY 1),
g     AS (SELECT QUANTILE_CONT(total_days, {p}) AS q, MEDIAN(total_days) AS m FROM train),
days  AS (SELECT DISTINCT purchase_date AS d FROM test),
lf    AS (SELECT d, COALESCE(MEDIAN(x.total_days), (SELECT m FROM g)) / (SELECT m FROM g) AS f
          FROM days LEFT JOIN f x ON x.is_delivered
           AND CAST(x.delivered_ts AS DATE) >= d - 14 AND CAST(x.delivered_ts AS DATE) < d
          GROUP BY d),
s     AS (SELECT t.*, COALESCE(CASE WHEN r.n >= 30 THEN r.q END, c.q, (SELECT q FROM g)) AS base_est, lf.f
          FROM test t
          LEFT JOIN route r USING (seller_state, customer_state)
          LEFT JOIN cst c USING (customer_state)
          JOIN lf ON lf.d = t.purchase_date)
SELECT COUNT(*) AS test_orders,
       AVG(is_late::INT) AS olist_late_rate, AVG(promised_days) AS olist_promised_days,
       AVG((CEIL(total_days) > CEIL(base_est))::INT) AS route_late_rate, AVG(CEIL(base_est)) AS route_promised_days,
       AVG((CEIL(total_days) > CEIL(base_est * GREATEST(f, 1)))::INT) AS load_late_rate,
       AVG(CEIL(base_est * GREATEST(f, 1))) AS load_promised_days
FROM s
"""


def main() -> int:
    con = duckdb.connect()
    con.execute(f"CREATE VIEW f AS SELECT * FROM read_parquet('{FCT}')")
    rows = []
    for p in PERCENTILES:
        r = con.execute(SQL.format(p=p)).df().iloc[0].to_dict()
        r["percentile"] = p
        rows.append(r)
    out = ROOT / "reports" / "backtest.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rows, indent=2, default=float))
    base = rows[0]
    print(f"Olist estimate: late {base['olist_late_rate']:.2%}, promised {base['olist_promised_days']:.1f} days "
          f"({int(base['test_orders']):,} test orders)")
    print(f"{'p':>5} {'route late':>11} {'days':>6} {'route+load late':>16} {'days':>6}")
    for r in rows:
        print(f"{r['percentile']:>5} {r['route_late_rate']:>11.2%} {r['route_promised_days']:>6.1f} "
              f"{r['load_late_rate']:>16.2%} {r['load_promised_days']:>6.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
