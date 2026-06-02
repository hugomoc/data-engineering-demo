select
    customer_id,
    name as customer_name,
    segment
from {{ source('ecommerce', 'customers') }}