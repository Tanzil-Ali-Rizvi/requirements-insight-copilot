# Data dictionary

Source: [Olist e-commerce public data](https://github.com/olist/work-at-olist-data) (MIT licence), orders placed Sep 2016 to Oct 2018. Built by `sql/01_staging.sql` and `sql/02_star_schema.sql`; exported to `data/warehouse/*.parquet`.

## fct_orders (99,441 rows, one per order)

| Column | Type | Meaning |
| --- | --- | --- |
| order_id | text | Order key |
| customer_id | text | Key to dim_customer |
| seller_id | text | Seller of the order's first item |
| order_status | text | delivered, shipped, canceled, unavailable, invoiced, processing, created, approved |
| purchase_ts / purchase_date / purchase_month | timestamp / date / date | When the order was placed |
| approved_ts | timestamp | Payment approved |
| carrier_ts | timestamp | Carrier's first scan (seller handoff) |
| delivered_ts | timestamp | Delivered to the customer |
| estimated_date | date | Promised delivery date shown to the customer |
| shipping_limit_ts | timestamp | Seller's handoff deadline (latest across items) |
| n_items, n_sellers | int | Items and distinct sellers on the order |
| items_value, freight_value, payment_value | BRL | Item prices, freight, total paid |
| review_score | 1-5 | Average review score for the order |
| customer_state / customer_region | text | Customer's state and IBGE region |
| seller_state / seller_region | text | First seller's state and region |
| same_state | bool | Customer and seller in the same state |
| is_delivered | bool | Status delivered and a delivery timestamp exists |
| is_late | bool | Delivery date after the promised date |
| days_vs_estimate | int | Delivery date minus promised date (negative = early) |
| promised_days | int | Promised date minus purchase date |
| total_days | float | Purchase to delivery |
| days_to_carrier | float | Purchase to carrier handoff |
| transit_days | float | Carrier handoff to delivery |
| seller_handoff_late | bool | Carrier handoff after the shipping limit |

## fct_order_items (112,650 rows, one per item)

order_id, order_item_id, product_id, seller_id, shipping_limit_ts, price, freight_value.

## Dimensions

| Table | Rows | Columns |
| --- | --- | --- |
| dim_customer | 99,441 | customer_id, customer_unique_id, city, state, region |
| dim_seller | 3,095 | seller_id, city, state, region |
| dim_product | 32,951 | product_id, category (English), weight_g |

## Privacy

Review text, zip codes in facts and geolocation are left out of the warehouse. Customer and seller IDs are Olist's anonymised hashes.
