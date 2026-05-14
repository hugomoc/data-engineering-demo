SELECT
    c.segment,
    SUM(o.amount) AS revenue
FROM orders o
JOIN customers c
    ON o.customer_id = c.customer_id
GROUP BY c.segment
ORDER BY revenue DESC;