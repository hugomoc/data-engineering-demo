SELECT
    p.product_name,
    SUM(o.amount) AS total_revenue,
    SUM(o.quantity) AS total_quantity
FROM incremental_orders o
JOIN products p
    ON o.product_id = p.product_id
GROUP BY p.product_name
ORDER BY total_revenue DESC;