-- models/marts/revenue/revenue_by_segment.sql
-- Segment mart at one row per customer segment for business mix questions.
SELECT
    segment,
    SUM(amount) AS revenue
FROM {{ ref('fct_sales') }} 
GROUP BY segment
