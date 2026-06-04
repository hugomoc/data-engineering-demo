SELECT
    strftime(order_date, '%Y-%m') AS month,
    SUM(amount) AS revenue
FROM incremental_orders
GROUP BY month
ORDER BY month;