{{ config(
    materialized='incremental',
    unique_key='order_id',
    on_schema_change='append_new_columns'
) }}

-- Core fact table for analytics. Grain: one row per order_id.
-- Staging models supply clean order, customer, and product fields; this model
-- denormalizes them so downstream marts and the API can query business-ready
-- sales data without repeating joins.

SELECT
    o.order_id,
    o.order_date,
    o.created_at,
    o.customer_id,
    o.product_id,
    o.quantity,
    o.amount,

    c.customer_name,
    c.segment,
    p.product_name,
    p.category

FROM {{ ref('stg_orders') }} o
LEFT JOIN {{ ref('stg_customers') }} c
    ON o.customer_id = c.customer_id
LEFT JOIN {{ ref('stg_products') }} p
    ON o.product_id = p.product_id

{% if is_incremental() %}

WHERE o.created_at > (
    SELECT coalesce(max(created_at), timestamp '1900-01-01')
    FROM {{ this }}
)

{% endif %}
