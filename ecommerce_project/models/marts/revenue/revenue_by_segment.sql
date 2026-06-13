-- models/marts/revenue/revenue_by_segment.sql
SELECT
    segment,
    SUM(amount) AS revenue
FROM {{ ref('fct_sales') }} 
GROUP BY segment
