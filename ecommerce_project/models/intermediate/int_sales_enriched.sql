-- Intermediate view used for enrichment checks: starts from the sales fact and
-- recalculates unit price from amount/quantity without changing the fact grain.
SELECT
    *,
    amount / NULLIF(quantity, 0) AS computed_unit_price
FROM {{ ref('fct_sales') }}
