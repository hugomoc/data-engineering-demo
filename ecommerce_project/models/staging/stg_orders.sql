-- Staging view for orders: keeps the raw order grain and selects only the
-- columns needed by the analytics model layer.
select
    order_id,
    customer_id,
    product_id,
    unit_price,
    quantity,
    amount,
    order_date,
    created_at
from {{ source('ecommerce', 'incremental_orders') }}
