select
    o.order_id,
    o.order_date,
    c.customer_name,
    c.segment,
    p.product_name,
    p.category,
    o.quantity,
    o.amount
from {{ ref('stg_orders') }} o
left join {{ ref('stg_customers') }} c
    on o.customer_id = c.customer_id
left join {{ ref('stg_products') }} p
    on o.product_id = p.product_id