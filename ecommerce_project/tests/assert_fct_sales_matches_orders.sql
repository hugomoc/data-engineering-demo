-- An earlier incremental filter silently dropped 97% of orders while every
-- other test passed. Reconcile identities, not only fact-table constraints.
select orders.order_id
from {{ ref('stg_orders') }} as orders
where not exists (
    select 1
    from {{ ref('fct_sales') }} as sales
    where sales.order_id = orders.order_id
)
