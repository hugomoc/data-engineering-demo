-- models/marts/revenue/monthly_revenue.sql
SELECT
    strftime(order_date, '%Y-%m') AS month,
    SUM(amount) AS revenue
FROM {{ ref('fct_sales') }}
GROUP BY month
