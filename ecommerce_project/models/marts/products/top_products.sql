-- models/marts/products/top_products.sql

SELECT
    product_name,
    SUM(quantity) AS units_sold,
    SUM(amount) AS revenue
FROM {{ ref('fct_sales') }}
GROUP BY 1
ORDER BY revenue DESC