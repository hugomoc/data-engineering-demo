-- models/marts/revenue/revenue_by_segment_month.sql
-- Segment/month mart for tracking revenue mix over time.
SELECT
    order_date,
    segment,
    SUM(amount) AS revenue
FROM {{ ref('fct_sales') }}
GROUP BY 1, 2
