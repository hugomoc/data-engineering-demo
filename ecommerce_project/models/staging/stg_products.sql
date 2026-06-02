select
    product_id,
    product_name,
    category
from {{ source('ecommerce', 'products') }}