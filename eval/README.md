# Agent evaluation on synthetic data

The question sheet contains **30 questions**, exactly five in each category:
`top_products`, `revenue_by_segment`, `monthly_revenue`, `anomalies_sales`,
`multi_tool`, and `out_of_scope`. Multi-tool labels name two tools; out-of-scope
labels are empty. **Labels are a DRAFT that a human must review.** Correct the
labels deliberately before using results to judge a planner change.

Run from the repository root with dependencies installed in `venv312`:

```sh
venv312/bin/python -m eval.run_agent_eval --offline
```

Offline is the default. It evaluates only `keyword_fallback`; it never invokes
the planner, analyst, or a provider client. It still builds the deterministic
300-order fixture and runs dbt in a unique system temporary directory. API tool
queries use that fixture in read-only mode; no development database is opened.
Temporary databases, compiled dbt output, and logs are removed afterward.

Live runs are manual. Supply `GEMINI_API_KEY` in the process environment first;
the evaluator does not load `.env` and exits non-zero when the key is absent.
Set `GEMINI_MODEL` to override the default `gemini-3.5-flash-lite` model.
Run outside pytest and its offline guard, which intentionally removes keys and
blocks sockets. These commands are for an explicit, user-initiated live run:

```sh
venv312/bin/python -m eval.run_agent_eval --live
venv312/bin/python -m eval.run_agent_eval --live --with-answers
```

Cost: **about 30 Gemini planner calls (30 more with --with-answers)** for a full
run. There is a two-second delay between questions (`--delay` must be positive).
On `ResourceExhausted`, evaluation stops without retrying or calling the next
question and writes how many questions completed. If the analyst exhausts quota,
that question's planner observation remains counted but its answer is incomplete.
Other unexpected exceptions fail the command rather than masquerading as a
completed evaluation. No live run has been performed for the initial report.

## What is measured

### Resuming an authorized live evaluation

Free-tier quotas can stop a run partway. For a manually authorized evaluation
across several days, supply `GEMINI_API_KEY` in the environment and run
`venv312/bin/python -m eval.run_agent_eval --live --resume` each day. This command
is documentation only; offline verification does not run it. The first resume
can start without a progress file, and subsequent runs print how many completed
IDs were skipped and retry failed IDs. Keep the question sheet and model fixed
between runs. Remove the progress file manually before starting a new evaluation.

`eval/results/live_progress.jsonl` is ignored and must never be committed. Each
line contains only an ID, classified outcome and allowlisted tools (before the
cap, so resumed cap metrics remain reproducible); keys and raw errors are never
stored. Resume restores planner selection, cap and fallback metrics, not previous
answer-faithfulness results. With `--with-answers`, only newly completed answers
enter that metric's denominator.

Quota, authentication and unavailable-model errors stop immediately and display
the exception class and a masked message. Other provider errors are retried once;
failed calls are never counted as answers or included in accuracy denominators.
The report counts failed attempts separately from questions never attempted,
marks incomplete runs as PARTIAL, and reports “no valid planner responses” when
none completed. An empty valid-tool parse remains a completed response: existing
application keyword routing is retained, with the raw empty result shown in the
out-of-scope metric. The existing silent-fallback row describes that routing,
not a swallowed provider failure.

- Exact-match tool-selection accuracy compares sets, ignoring tool order.
- Precision and recall are computed per question and then averaged. Both empty
  is perfect; an empty/nonempty mismatch gets zero for both.
- Per-category results are counts, **k of 5**, with a completed-question count.
  Overall accuracy includes a Wilson 95% interval and n. Binary rates use Wilson
  intervals. Macro precision/recall use the same formula with fractional
  effective successes; those bounds are descriptive, not binomial guarantees.
- Model-only out-of-scope handling counts returned responses that contained no
  valid tool, **before fallback**, among observed out-of-scope responses. Provider
  errors are reported separately. This differs from final routed-tool accuracy:
  existing fallback can still send an out-of-scope question to monthly revenue.
- Silent monthly fallback excludes genuine model selections of monthly revenue.
  The cap count observes more than three unique valid tools before truncation,
  after invented names and duplicates have been removed. Both are unmeasured
  offline; the offline monthly keyword-default rate is shown separately.

The real planner and analyst functions are reused with their existing prompts
and model name. Evaluation observes model output and quota errors through a
temporary wrapper; it does not change application fallback behavior.

## Numerical correctness and answer faithfulness

`tests/test_tool_numbers.py` builds a temporary fixture and dbt models, then
compares every API tool and its metrics with independent SQL against staging
orders/products or the fact table. These offline CI tests check product revenue
and shares, customer-segment shares, the latest monthly delta, and anomaly months.
They skip explicitly if dbt is missing; they never score a question with an LLM.

With `--with-answers`, dollar (`$`) and percentage (`%`) figures in each answer
must match some numeric value in `raw_data` or `computed_data` within half the
last displayed digit, including K/M/B abbreviations. The reported rate includes
only answers containing such figures; figure-free answers are counted separately.
This is a **heuristic**: it does not establish correct attribution, units,
reasoning, completeness, or prose truth. Spelled-out quantities are not checked,
and coincidental numeric matches can pass. Rounding to a coarse unit broadens
the tolerance. These results do not replace human answer review.

## Results

Every successful or quota-stopped run overwrites `eval/results/latest.md` with
aggregate metrics and an ID/expected/got/pass-fail table. Save a copy before
comparing runs. Synthetic results may be committed; databases, logs and keys
must not be committed. The current report is an offline keyword baseline,
marked **pending first live run** for live planner accuracy.

```sh
venv312/bin/pytest -q tests/test_planner_parsing.py tests/test_tool_numbers.py tests/test_eval_metrics.py
```
