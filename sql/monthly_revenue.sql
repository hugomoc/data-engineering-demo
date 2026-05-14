SELECT
    strftime(order_date, '%Y-%m') AS month,
    SUM(amount) AS revenue
FROM orders
GROUP BY month
ORDER BY month;