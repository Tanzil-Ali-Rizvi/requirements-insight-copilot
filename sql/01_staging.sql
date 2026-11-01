-- 01_staging.sql
-- Raw Olist CSVs -> typed staging views. {raw} is replaced with the raw-data folder.

CREATE OR REPLACE VIEW stg_orders AS
SELECT
    order_id,
    customer_id,
    order_status,
    CAST(order_purchase_timestamp      AS TIMESTAMP) AS purchase_ts,
    CAST(order_approved_at             AS TIMESTAMP) AS approved_ts,
    CAST(order_delivered_carrier_date  AS TIMESTAMP) AS carrier_ts,
    CAST(order_delivered_customer_date AS TIMESTAMP) AS delivered_ts,
    CAST(order_estimated_delivery_date AS DATE)      AS estimated_date
FROM read_csv_auto('{raw}/olist_orders_dataset.csv');

CREATE OR REPLACE VIEW stg_order_items AS
SELECT
    order_id,
    CAST(order_item_id AS INTEGER)            AS order_item_id,
    product_id,
    seller_id,
    CAST(shipping_limit_date AS TIMESTAMP)    AS shipping_limit_ts,
    CAST(price AS DOUBLE)                     AS price,
    CAST(freight_value AS DOUBLE)             AS freight_value
FROM read_csv_auto('{raw}/olist_order_items_dataset.csv');

CREATE OR REPLACE VIEW stg_customers AS
SELECT customer_id, customer_unique_id, customer_zip_code_prefix AS zip_prefix,
       customer_city AS city, customer_state AS state
FROM read_csv_auto('{raw}/olist_customers_dataset.csv');

CREATE OR REPLACE VIEW stg_sellers AS
SELECT seller_id, seller_zip_code_prefix AS zip_prefix, seller_city AS city, seller_state AS state
FROM read_csv_auto('{raw}/olist_sellers_dataset.csv');

CREATE OR REPLACE VIEW stg_products AS
SELECT p.product_id,
       COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
       CAST(p.product_weight_g AS DOUBLE) AS weight_g
FROM read_csv_auto('{raw}/olist_products_dataset.csv') p
LEFT JOIN read_csv_auto('{raw}/product_category_name_translation.csv') t
       ON p.product_category_name = t.product_category_name;

-- Review text is dropped on purpose: only the score is needed and it keeps the warehouse free of free text.
CREATE OR REPLACE VIEW stg_reviews AS
SELECT order_id, AVG(CAST(review_score AS DOUBLE)) AS review_score
FROM read_csv_auto('{raw}/olist_order_reviews_dataset.csv')
GROUP BY order_id;

CREATE OR REPLACE VIEW stg_payments AS
SELECT order_id, SUM(CAST(payment_value AS DOUBLE)) AS payment_value
FROM read_csv_auto('{raw}/olist_order_payments_dataset.csv')
GROUP BY order_id;

-- IBGE macro-regions of Brazil.
CREATE OR REPLACE TABLE ref_state_region AS
SELECT * FROM (VALUES
    ('AC','North'),('AP','North'),('AM','North'),('PA','North'),('RO','North'),('RR','North'),('TO','North'),
    ('AL','Northeast'),('BA','Northeast'),('CE','Northeast'),('MA','Northeast'),('PB','Northeast'),
    ('PE','Northeast'),('PI','Northeast'),('RN','Northeast'),('SE','Northeast'),
    ('DF','Center-West'),('GO','Center-West'),('MT','Center-West'),('MS','Center-West'),
    ('ES','Southeast'),('MG','Southeast'),('RJ','Southeast'),('SP','Southeast'),
    ('PR','South'),('RS','South'),('SC','South')
) AS t(state, region);
