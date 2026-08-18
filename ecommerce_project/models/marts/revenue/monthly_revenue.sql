-- models/marts/revenue/monthly_revenue.sql
-- Revenue mart at one row per calendar month, used by the API for trend and
-- anomaly questions.
SELECT
    strftime(order_date, '%Y-%m') AS month,
    SUM(amount) AS revenue
FROM {{ ref('fct_sales') }}
GROUP BY month
