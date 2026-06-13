{{ config(
    materialized='incremental',
    unique_key='order_id'
) }}

-- Grain: one row per order_id

SELECT
    o.order_id,
    o.order_date,
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

WHERE o.order_id > (
    SELECT MAX(order_id)
    FROM {{ this }}
)

{% endif %}