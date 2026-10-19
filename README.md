# Data Engineering Demo: Modern ELT + AI Analytics Platform
(dbt • Prefect • DuckDB • FastAPI • LLMs)

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Orchestration](https://img.shields.io/badge/Orchestration-Prefect-purple)
![Transformations](https://img.shields.io/badge/Transformations-dbt-orange)
![Warehouse](https://img.shields.io/badge/Warehouse-DuckDB-yellow)
![API](https://img.shields.io/badge/API-FastAPI-green)
![AI](https://img.shields.io/badge/LLM-Gemini%20gemini--3.5--flash--lite%20%28configurable%29-black)
[![CI](https://github.com/hugomoc/data-engineering-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/hugomoc/data-engineering-demo/actions/workflows/ci.yml)

---

## Overview

This project is a production-style end-to-end analytics engineering system simulating an e-commerce data platform.
It combines modern data engineering practices with an AI-powered analytics interface, enabling both SQL-based and natural language querying of business metrics.
The system demonstrates a full ELT + Analytics + AI serving layer architecture.

---

## Demo

https://github.com/user-attachments/assets/55b07ce9-d5ea-4961-a251-fd52f7bf4ded





---

## Architecture


            +----------------------+
            |   CSV Data Sources   |
            +----------+-----------+
                       |
                       v
            +----------------------+
            |  Python Ingestion    |
            | (Incremental Loads)  |
            +----------+-----------+
                       |
                       v
            +----------------------+
            |      DuckDB          |
            |   Analytical Store   |
            +----------+-----------+
                       |
                       v
            +----------------------+
            |        dbt           |
            | Models + Tests +     |
            | Transformations      |
            +----------+-----------+
                       |
                       v
         +-----------------------------+
         |     Serving & AI Layer      |
         | FastAPI + SQL + LLM Agent   |
         +-----------------------------+

---


---

## System Components

### 1. Data Ingestion Layer (Python)
- Incremental CSV ingestion with file tracking
- Prevents duplicate processing
- Batch-oriented ELT simulation
- Designed for extensibility into streaming ingestion

---

### 2. Orchestration Layer (Prefect)
- Manages end-to-end pipeline execution:
  - ingest → validate → transform
- Supports scheduled runs via cron deployments
- Provides observability through Prefect UI
- Handles task dependencies and failure recovery

---

### 3. Analytical Warehouse (DuckDB)
- Embedded OLAP engine for local analytics
- Serves as the central storage layer
- Optimized for fast columnar SQL execution
- Eliminates need for external warehouse in local environments

---

### 4. Transformation Layer (dbt)
Implements a layered analytics architecture:

- **Staging models** → raw normalization
- **Intermediate models** → business logic enrichment
- **Mart models** → analytics-ready datasets

Key outputs:
- `fct_sales`
- `mart_customer_ltv`
- `top_products`
- `monthly_revenue`
- `revenue_by_segment`

Includes:
- Data tests (uniqueness, not-null, referential integrity)
- Modular SQL architecture
- Reusable transformation logic

---

### 5. Serving Layer (FastAPI + AI Agent)
The API exposes both structured analytics and AI-powered insights.
📊 REST Endpoints
- /top-products
- /monthly-revenue
- /revenue-by-segment

---

## AI Analytics Layer (/agent)

This system includes an LLM-powered analytics agent that acts as a natural language interface to the data warehouse.
🧩 Agent Architecture

User Question
     ↓
Planner Node (tool selection)
     ↓
Tool Node (DuckDB execution)
     ↓
Compute Node (business metrics)
     ↓
Analyst Node (LLM insights)


🧠 Capabilities
* Natural language → metric routing
* Multi-tool execution (when needed)
* Automated KPI computation
* Business insight generation
* Context-aware session handling

💬 Example
User:
What are the top products this month?
System Flow:
1. LLM identifies top_products tool
2. Executes DuckDB query
3. Computes revenue contribution %
4. Generates business explanation via LLM
Output:
* Structured metrics
* Business insights
* Contribution analysis

## Tech Stack

* Python 3.12
* FastAPI
* DuckDB
* dbt-core
* Prefect
* Gemini (`GEMINI_MODEL`, default `gemini-3.5-flash-lite`)
* SQL (core analytics logic)

---

## How to run

After pulling this change, run `dbt run --full-refresh -s fct_sales+` once from
`ecommerce_project/` to rebuild existing facts with the `created_at` watermark.

```sh
python -m venv venv312
source venv312/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set GEMINI_API_KEY in .env before asking the agent a question.
```

The checked-in `ecommerce_project/profiles.yml` defaults to the DuckDB `dev`
target. Run dbt from `ecommerce_project/` with that profile directory; its default
database is `ecommerce_project/dev.duckdb`. Set `DUCKDB_PATH` to an absolute path
to build against another database. The `prod` target uses `prod.duckdb`.

```sh
python pipeline/prefect_flow.py
(cd ecommerce_project && DBT_PROFILES_DIR=. dbt build)
uvicorn api.main:app --reload
# In a second terminal with the environment activated:
streamlit run app.py
# Offline regression tests (temporary data and databases):
pytest -q
```

The UI uses `API_URL` when set, otherwise `http://127.0.0.1:8000`.

## Data quality

- dbt reconciliation checks both directions: every staged order must reach
  `fct_sales`, and every fact order must exist in the staged source. These tests
  catch missing orders and orphan facts that uniqueness and not-null tests miss.
- The Python source gate raises `DataQualityError` for null order IDs, duplicate
  order IDs, or an empty `incremental_orders` table. The Prefect validation task
  fails before dbt runs. Set `DEMO_DB_PATH` to check a separate database.
- The incremental regression builds 30 UUID orders, adds 30 later-timestamped
  orders, and verifies all 60 survive. It then deletes five disposable fact rows
  and requires the missing-order reconciliation test to fail with five results.
- CI runs offline pytest checks and `dbt build` against 300 deterministic orders
  spanning three months. Tests use their own temporary databases; the CI fixture
  uses `/tmp/ded-ci.duckdb` and refuses to overwrite an existing file. Python test
  and dbt processes block network access and do not need Gemini credentials.

### Bug found and fixed

the incremental fct_sales filter compared string order_ids with >, so in my dev database 2,243 of 2,307 orders (97.2%) never reached the fact table; filtering on the load timestamp fixed it; after a full refresh the source and fact counts match (2,307 = 2,307, 0 missing)

These figures describe the recorded development repair; CI verification uses
synthetic temporary data and does not open the development database.

## Agent evaluation

The draft evaluation sheet contains **30 questions**, five each for product,
segment, monthly-revenue, anomaly, multi-tool, and out-of-scope cases. Offline CI
covers planner parsing and numeric correctness against independent fixture SQL.
Live planner accuracy is measured manually; results live in
`eval/results/latest.md`, marked **pending first live run** for now.

```sh
venv312/bin/python -m eval.run_agent_eval --offline
```

A manual live run costs **about 30 Gemini planner calls (30 more with --with-answers)**.
See `eval/README.md` for live commands, label review, metric definitions, quota
handling, and the limitations of the numerical answer-faithfulness heuristic.
The three-tool cap was added after the evaluation work found that the prompt
and parser disagreed.

For an explicitly authorized live evaluation across several days, run
`venv312/bin/python -m eval.run_agent_eval --live --resume` on each day with
`GEMINI_API_KEY` supplied in the environment. Free-tier quotas can stop a run
partway; authentication and unavailable-model errors also stop immediately.
Other provider failures are retried once. Failed calls are never counted as
answers or included in accuracy denominators. The report marks partial runs and
separates failed calls from questions not run.

Resume skips completed IDs stored in the ignored
`eval/results/live_progress.jsonl` and retries failed IDs. The file stores only
IDs, outcomes and valid tool names, never keys or error messages. Keep the same
question sheet and model across resumed runs; remove the progress file manually
to start a fresh evaluation. Resumed planner results retain cap and fallback
metrics, but previous answer-faithfulness results are not stored or restored.

Raw observations distinguish `declined` (parsing found no valid tool), `picked`
(valid tools were named, counted before the cap), and `no_text` (reading the
response text raised). `no_text` is reported separately from failed API calls.
“Got” shows the final tools after the app's fallback and cap. Old progress files
lacking raw statuses must be archived outside the repo before starting a new run;
their empty tool lists cannot distinguish a decline from unreadable text.

## Design principles

This project follows modern data engineering principles including separation of ingestion, transformation, and serving layers, modular SQL modeling with dbt, lightweight analytics storage using DuckDB, and AI-assisted analytics for business interpretation. It is designed to be extensible, reproducible, and representative of production-style ELT architectures.

## Business Use Cases

- Product performance analysis
- Revenue tracking (monthly + segment-based)
- Customer lifetime value (CLV)
- Sales funnel analytics
- Self-service analytics via natural language

## Future improvements

Planned enhancements include CI/CD integration with GitHub Actions, Docker containerization, cloud deployment, streaming ingestion simulation, anomaly detection improvements, and enhanced observability and monitoring.

## Author

Hugo Batista – Data Engineer focused on analytics engineering, ELT pipelines, and AI-powered data systems.

GitHub: https://github.com/hugomoc/data-engineering-demo
