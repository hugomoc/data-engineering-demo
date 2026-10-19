# Agent evaluation

Mode: **live**; 30 of 30 questions completed.
Model: gemini-3.5-flash-lite
Labels are a DRAFT that a human must review.

| Metric | Result |
| --- | --- |
| Exact-match tool-selection accuracy (final tools after app fallback and cap) | 83.3% (95% Wilson 66.4%–92.7%; n=30) |
| Mean per-question precision (final tools after app fallback and cap) | 83.3% (95% Wilson 66.4%–92.7%; n=30) |
| Mean per-question recall (final tools after app fallback and cap) | 83.3% (95% Wilson 66.4%–92.7%; n=30) |
| Out-of-scope: model declined | 2 of 5 |
| Out-of-scope: model picked tools | 2 of 5 |
| Out-of-scope: no usable response | 1 of 5 |
| Final tools came from keyword fallback after the model declined | 2 of 30 |
| Final tools came from keyword fallback after no usable response | 1 of 30 |
| Questions with no usable model text | 1 of 30 |
| Three-tool cap applied | 0.0% (95% Wilson 0.0%–11.4%; n=30) |
| Questions with cap applied (count) | 0 of 30 |
| Planner errors (count) | 0 |
| Failed calls (count) | 0 |
| Questions not run (count) | 0 |

Macro precision/recall bounds use fractional effective successes and are descriptive Wilson-style bounds, not binomial confidence guarantees.
Tool order is ignored for accuracy; empty/empty scores 1, and an empty/nonempty mismatch scores 0.

| Category | Correct (final tools after app fallback and cap) | Completed |
| --- | --- | --- |
| top_products | 5 of 5 | 5 |
| revenue_by_segment | 5 of 5 | 5 |
| monthly_revenue | 5 of 5 | 5 |
| anomalies_sales | 5 of 5 | 5 |
| multi_tool | 5 of 5 | 5 |
| out_of_scope | 0 of 5 | 5 |

| ID | Expected | Model raw | Got (final) | Response metadata | Pass/fail |
| --- | --- | --- | --- | --- | --- |
| Q01 | top_products | top_products | top_products | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q02 | top_products | top_products | top_products | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q03 | top_products | top_products | top_products | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q04 | top_products | top_products | top_products | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q05 | top_products | top_products | top_products | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q06 | revenue_by_segment | revenue_by_segment | revenue_by_segment | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q07 | revenue_by_segment | revenue_by_segment | revenue_by_segment | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q08 | revenue_by_segment | revenue_by_segment | revenue_by_segment | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q09 | revenue_by_segment | revenue_by_segment | revenue_by_segment | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q10 | revenue_by_segment | revenue_by_segment | revenue_by_segment | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q11 | monthly_revenue | monthly_revenue | monthly_revenue | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q12 | monthly_revenue | monthly_revenue | monthly_revenue | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q13 | monthly_revenue | monthly_revenue | monthly_revenue | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q14 | monthly_revenue | monthly_revenue | monthly_revenue | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q15 | monthly_revenue | monthly_revenue | monthly_revenue | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q16 | anomalies_sales | anomalies_sales | anomalies_sales | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q17 | anomalies_sales | anomalies_sales | anomalies_sales | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q18 | anomalies_sales | anomalies_sales | anomalies_sales | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q19 | anomalies_sales | anomalies_sales | anomalies_sales | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q20 | anomalies_sales | anomalies_sales | anomalies_sales | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q21 | top_products, revenue_by_segment | top_products, revenue_by_segment | top_products, revenue_by_segment | valid_tool_count=2; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q22 | monthly_revenue, top_products | monthly_revenue, top_products | monthly_revenue, top_products | valid_tool_count=2; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q23 | revenue_by_segment, monthly_revenue | revenue_by_segment, monthly_revenue | revenue_by_segment, monthly_revenue | valid_tool_count=2; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q24 | monthly_revenue, anomalies_sales | monthly_revenue, anomalies_sales | monthly_revenue, anomalies_sales | valid_tool_count=2; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q25 | top_products, anomalies_sales | top_products, anomalies_sales | top_products, anomalies_sales | valid_tool_count=2; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | PASS |
| Q26 | [] | [] | monthly_revenue | valid_tool_count=0; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | FAIL |
| Q27 | [] | no text | monthly_revenue | text_error=ValueError; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | FAIL |
| Q28 | [] | [] | monthly_revenue | valid_tool_count=0; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | FAIL |
| Q29 | [] | revenue_by_segment, monthly_revenue, top_products | revenue_by_segment, monthly_revenue, top_products | valid_tool_count=3; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | FAIL |
| Q30 | [] | monthly_revenue | monthly_revenue | valid_tool_count=1; block_reason=BLOCK_REASON_UNSPECIFIED; finish_reason=STOP | FAIL |
