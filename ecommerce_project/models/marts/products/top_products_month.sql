-- models/marts/products/top_products_month.sql
-- Product/month mart for trend analysis of units sold and revenue.
SELECT
    order_date,
    product_name,
    SUM(quantity) AS units_sold,
    SUM(amount) AS revenue
FROM {{ ref('fct_sales') }}
GROUP BY 1,2
ORDER BY revenue DESC
