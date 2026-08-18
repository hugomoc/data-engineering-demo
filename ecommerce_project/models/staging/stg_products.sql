-- Staging view for products: exposes product attributes at one row per
-- source product_id without applying business aggregation.
select
    product_id,
    product_name,
    category
from {{ source('ecommerce', 'products') }}
