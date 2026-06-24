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

This project is a production-style end-to-end analytics engineering system simulating an e-commerce data platform.
It combines modern data engineering practices with an AI-powered analytics interface, enabling both SQL-based and natural language querying of business metrics.
The system demonstrates a full ELT + Analytics + AI serving layer architecture.

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
* Gemini / GPT-style LLMs
* SQL (core analytics logic)

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
