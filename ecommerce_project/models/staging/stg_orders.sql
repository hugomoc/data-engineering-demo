select
    order_id,
    customer_id,
    product_id,
    unit_price,
    quantity,
    amount,
    order_date
from {{ source('ecommerce', 'incremental_orders') }}