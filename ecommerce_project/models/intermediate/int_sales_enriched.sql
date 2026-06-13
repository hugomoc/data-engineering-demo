SELECT
    *,
    amount / NULLIF(quantity, 0) AS computed_unit_price
FROM {{ ref('fct_sales') }}