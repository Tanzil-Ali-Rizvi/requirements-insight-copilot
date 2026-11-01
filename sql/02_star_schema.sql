-- 02_star_schema.sql
-- Star schema: three dimensions and two facts. fct_orders is one row per order with every
-- delivery-timing measure the analysis and the copilot need.

CREATE OR REPLACE TABLE dim_customer AS
SELECT c.customer_id, c.customer_unique_id, c.city, c.state, r.region
FROM stg_customers c LEFT JOIN ref_state_region r USING (state);

CREATE OR REPLACE TABLE dim_seller AS
SELECT s.seller_id, s.city, s.state, r.region
FROM stg_sellers s LEFT JOIN ref_state_region r USING (state);

CREATE OR REPLACE TABLE dim_product AS
SELECT product_id, category, weight_g FROM stg_products;

CREATE OR REPLACE TABLE fct_order_items AS
SELECT i.order_id, i.order_item_id, i.product_id, i.seller_id,
       i.shipping_limit_ts, i.price, i.freight_value
FROM stg_order_items i;

CREATE OR REPLACE TABLE fct_orders AS
WITH items AS (
    SELECT order_id,
           COUNT(*)                         AS n_items,
           COUNT(DISTINCT seller_id)        AS n_sellers,
           SUM(price)                       AS items_value,
           SUM(freight_value)               AS freight_value,
           MAX(shipping_limit_ts)           AS shipping_limit_ts,
           ARG_MIN(seller_id, order_item_id) AS seller_id
    FROM stg_order_items
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.customer_id,
    i.seller_id,
    o.order_status,
    o.purchase_ts,
    CAST(o.purchase_ts AS DATE)                                   AS purchase_date,
    DATE_TRUNC('month', o.purchase_ts)::DATE                      AS purchase_month,
    o.approved_ts,
    o.carrier_ts,
    o.delivered_ts,
    o.estimated_date,
    i.shipping_limit_ts,
    i.n_items,
    i.n_sellers,
    i.items_value,
    i.freight_value,
    p.payment_value,
    rv.review_score,
    c.state                                                       AS customer_state,
    c.region                                                      AS customer_region,
    s.state                                                       AS seller_state,
    s.region                                                      AS seller_region,
    (c.state = s.state)                                           AS same_state,
    -- Delivery measures (NULL unless the order was delivered)
    (o.order_status = 'delivered' AND o.delivered_ts IS NOT NULL) AS is_delivered,
    CASE WHEN o.delivered_ts IS NOT NULL
         THEN CAST(o.delivered_ts AS DATE) > o.estimated_date END AS is_late,
    CASE WHEN o.delivered_ts IS NOT NULL
         THEN DATE_DIFF('day', o.estimated_date, CAST(o.delivered_ts AS DATE)) END AS days_vs_estimate,
    DATE_DIFF('day', CAST(o.purchase_ts AS DATE), o.estimated_date)            AS promised_days,
    DATE_DIFF('hour', o.purchase_ts, o.delivered_ts) / 24.0                    AS total_days,
    DATE_DIFF('hour', o.purchase_ts, o.carrier_ts) / 24.0                      AS days_to_carrier,
    DATE_DIFF('hour', o.carrier_ts, o.delivered_ts) / 24.0                     AS transit_days,
    -- Seller handed the parcel to the carrier after the shipping limit
    CASE WHEN o.carrier_ts IS NOT NULL
         THEN o.carrier_ts > i.shipping_limit_ts END                           AS seller_handoff_late
FROM stg_orders o
LEFT JOIN items        i  USING (order_id)
LEFT JOIN stg_payments p  USING (order_id)
LEFT JOIN stg_reviews  rv USING (order_id)
LEFT JOIN dim_customer c  USING (customer_id)
LEFT JOIN dim_seller   s  ON s.seller_id = i.seller_id;
