# Agent evaluation

Mode: **offline**; 30 of 30 questions completed.
Model: none (keyword_fallback only)
Labels are a DRAFT that a human must review.

**Live planner accuracy: pending first live run.**
This run evaluates only keyword_fallback; no planner or analyst was called.

| Metric | Result |
| --- | --- |
| keyword_fallback baseline (not the LLM): exact-match tool selection | 53.3% (95% Wilson 36.1%–69.8%; n=30) |
| keyword_fallback baseline (not the LLM): mean precision | 70.0% (95% Wilson 52.1%–83.3%; n=30) |
| keyword_fallback baseline (not the LLM): mean recall | 61.7% (95% Wilson 43.9%–76.8%; n=30) |
| Model selected no valid tool on out-of-scope input, before fallback | not measured (n=0) |
| Silent monthly_revenue fallback | not measured (n=0) |
| Three-tool cap applied | not measured (n=0) |
| Keyword fallback returned monthly_revenue (not a model observation) | 46.7% (95% Wilson 30.2%–63.9%; n=30) |

Macro precision/recall bounds use fractional effective successes and are descriptive Wilson-style bounds, not binomial confidence guarantees.
Tool order is ignored for accuracy; empty/empty scores 1, and an empty/nonempty mismatch scores 0.

| Category | Correct | Completed |
| --- | --- | --- |
| top_products | 4 of 5 | 5 |
| revenue_by_segment | 4 of 5 | 5 |
| monthly_revenue | 5 of 5 | 5 |
| anomalies_sales | 3 of 5 | 5 |
| multi_tool | 0 of 5 | 5 |
| out_of_scope | 0 of 5 | 5 |

| ID | Expected | Got | Pass/fail |
| --- | --- | --- | --- |
| Q01 | top_products | top_products | PASS |
| Q02 | top_products | top_products | PASS |
| Q03 | top_products | top_products | PASS |
| Q04 | top_products | top_products | PASS |
| Q05 | top_products | monthly_revenue | FAIL |
| Q06 | revenue_by_segment | revenue_by_segment | PASS |
| Q07 | revenue_by_segment | revenue_by_segment | PASS |
| Q08 | revenue_by_segment | revenue_by_segment | PASS |
| Q09 | revenue_by_segment | revenue_by_segment | PASS |
| Q10 | revenue_by_segment | monthly_revenue | FAIL |
| Q11 | monthly_revenue | monthly_revenue | PASS |
| Q12 | monthly_revenue | monthly_revenue | PASS |
| Q13 | monthly_revenue | monthly_revenue | PASS |
| Q14 | monthly_revenue | monthly_revenue | PASS |
| Q15 | monthly_revenue | monthly_revenue | PASS |
| Q16 | anomalies_sales | anomalies_sales | PASS |
| Q17 | anomalies_sales | anomalies_sales | PASS |
| Q18 | anomalies_sales | anomalies_sales | PASS |
| Q19 | anomalies_sales | monthly_revenue | FAIL |
| Q20 | anomalies_sales | monthly_revenue | FAIL |
| Q21 | top_products, revenue_by_segment | revenue_by_segment | FAIL |
| Q22 | monthly_revenue, top_products | top_products | FAIL |
| Q23 | revenue_by_segment, monthly_revenue | revenue_by_segment | FAIL |
| Q24 | monthly_revenue, anomalies_sales | anomalies_sales | FAIL |
| Q25 | top_products, anomalies_sales | top_products | FAIL |
| Q26 | [] | monthly_revenue | FAIL |
| Q27 | [] | monthly_revenue | FAIL |
| Q28 | [] | monthly_revenue | FAIL |
| Q29 | [] | monthly_revenue | FAIL |
| Q30 | [] | monthly_revenue | FAIL |
