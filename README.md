# Data Engineering Demo: Modern ELT + AI Analytics Platform
(dbt • Prefect • DuckDB • FastAPI • LLMs)

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Orchestration](https://img.shields.io/badge/Orchestration-Prefect-purple)
![Transformations](https://img.shields.io/badge/Transformations-dbt-orange)
![Warehouse](https://img.shields.io/badge/Warehouse-DuckDB-yellow)
![API](https://img.shields.io/badge/API-FastAPI-green)
![AI](https://img.shields.io/badge/LLM-GPT--4o--mini-black)

---

## Overview

This project is a production-style **end-to-end analytics engineering system** that simulates an e-commerce data platform.

It demonstrates a modern ELT architecture combining:

- Orchestrated ingestion pipelines (Prefect)
- Modular transformation layer (dbt)
- Lightweight analytical warehouse (DuckDB)
- Analytics serving API (FastAPI)
- LLM-powered natural language analytics interface

The system supports both **SQL-based analytics workflows** and **natural language querying of business metrics**.

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
            +----------------------+
            |   Analytics Layer    |
            | SQL + FastAPI + LLM  |
            +----------------------+

---


---

## System Components

### 1. Data Ingestion Layer (Python + Prefect)
- Incremental CSV ingestion with file tracking
- Prevents duplicate processing
- Designed for batch-oriented ELT workloads
- Integrated with Prefect for orchestration, retries, and scheduling

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

### 5. Serving Layer (FastAPI)
Exposes analytics through REST endpoints:

- `/top-products`
- `/monthly-revenue`
- `/revenue-by-segment`
- `/ask` (LLM-powered analytics interface)

This layer bridges:
- SQL analytics
- Business consumption
- Natural language interaction

---

## AI Analytics Layer (LLM-Powered)

The system includes an AI interface powered by GPT-4o-mini for natural language analytics.

### Capabilities

- Natural language → metric routing
- Dynamic SQL execution via dbt/DuckDB layer
- KPI explanation generation
- Business insight summarization
- Context-aware follow-up questions (session-based)

### Example Flow

**User question:**
> What are the top products this month?

**System execution:**
1. LLM classifies intent (product analytics)
2. Routes to dbt model / SQL query
3. Executes against DuckDB
4. Returns structured results
5. LLM generates business interpretation

---

## Tech Stack

- Python 3.12
- Prefect (workflow orchestration)
- dbt-core (analytics engineering)
- DuckDB (analytical warehouse)
- FastAPI (serving layer)
- OpenAI GPT-4o-mini (LLM layer)
- SQL (core transformation logic)

---

## How to run

pip install -r requirements.txt

python pipeline/prefect_flow.py

cd ecommerce_project && dbt run && dbt test

uvicorn api.main:app --reload

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
