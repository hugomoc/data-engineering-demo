-- Staging view for customers: light renaming only, preserving one row per
-- source customer_id for downstream relationship tests and joins.
select
    customer_id,
    name as customer_name,
    segment
from {{ source('ecommerce', 'customers') }}
