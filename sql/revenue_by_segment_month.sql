SELECT
	o.order_date,
    c.segment,
    SUM(o.amount) AS revenue
FROM incremental_orders o
JOIN customers c
    ON o.customer_id = c.customer_id
GROUP BY o.order_date, c.segment
ORDER BY revenue DESC;