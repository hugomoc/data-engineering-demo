-- Every fact order must still have a corresponding source order.
select sales.*
from {{ ref('fct_sales') }} as sales
where not exists (
    select 1
    from {{ ref('stg_orders') }} as orders
    where orders.order_id = sales.order_id
)
