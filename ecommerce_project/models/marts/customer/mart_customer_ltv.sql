-- Customer mart at one row per customer_id/customer_name/segment.
-- Summarizes lifetime value and order count for customer-level analysis.
SELECT
    customer_id,
    customer_name,
    segment,
    SUM(amount) AS lifetime_value,
    COUNT(*) AS total_orders
FROM {{ ref('fct_sales') }}
GROUP BY 1,2,3
