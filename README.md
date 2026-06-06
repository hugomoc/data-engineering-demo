# Data Engineering Demo: Modern ELT + AI Analytics Platform (dbt, Prefect, DuckDB, FastAPI)

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Prefect](https://img.shields.io/badge/Orchestration-Prefect-purple)
![dbt](https://img.shields.io/badge/Transformations-dbt-orange)
![DuckDB](https://img.shields.io/badge/Warehouse-DuckDB-yellow)
![FastAPI](https://img.shields.io/badge/API-FastAPI-green)
![OpenAI](https://img.shields.io/badge/AI-GPT--4o--mini-black)

---

## Overview

This project is an end-to-end **modern data engineering and AI analytics platform** that simulates an e-commerce analytics system.

It combines:
- ELT data pipelines (Python + Prefect)
- Analytics engineering models (dbt)
- Local analytical warehouse (DuckDB)
- API layer (FastAPI)
- LLM-powered analytics assistant (OpenAI GPT-4o-mini)

The system allows both **SQL-based analytics** and **natural language querying of business metrics**.

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

## Key Features

### 1. Data Ingestion (Python)
- Reads raw CSV e-commerce data
- Performs incremental loading
- Prevents duplicate processing using file tracking
- Produces analytics-ready datasets

---

### 2. Workflow Orchestration (Prefect)
- Automates full pipeline execution
- Manages task dependencies (load → validate → transform)
- Provides retries, logging, and scheduling via cron deployments

---

### 3. Data Warehouse (DuckDB)
- Lightweight analytical database
- Supports fast SQL execution locally
- Acts as central storage for transformations

---

### 4. Analytics Engineering (dbt)
- Modular SQL transformation layer
- Staging and analytics models
- Data testing for quality validation
- Snapshotting and reusable metrics logic

---

### 5. API Layer (FastAPI)
Exposes analytical results via REST endpoints:

- `/top-products`
- `/revenue-by-segment`
- `/monthly-revenue`
- `/ask` (AI-powered analytics interface)

---

## AI-Powered Analytics Layer

This project includes an LLM-powered analytics interface that enables natural language querying of business metrics.

### Capabilities

- Natural language → metric routing using GPT-4o-mini
- Context-aware analytics conversations (session memory)
- Automated KPI explanations from query results
- Month-over-month comparison reasoning
- Business insight generation from SQL outputs

### Example

**User:**

> What are the top products?

**System:**
- Routes question to correct dbt/SQL model
- Executes DuckDB query
- Returns structured results + LLM-generated insight

---

## Tech Stack

- Python 3.12
- Prefect (orchestration)
- dbt-core (transformations)
- DuckDB (warehouse)
- FastAPI (API layer)
- OpenAI GPT-4o-mini (AI layer)
- SQL (analytics)

---

## How to run

pip install -r requirements.txt

python pipeline/prefect_flow.py

cd ecommerce_project && dbt run && dbt test

uvicorn api.main:app --reload

## Design principles

This project follows modern data engineering principles including separation of ingestion, transformation, and serving layers, modular SQL modeling with dbt, lightweight analytics storage using DuckDB, and AI-assisted analytics for business interpretation. It is designed to be extensible, reproducible, and representative of production-style ELT architectures.

## Future improvements

Planned enhancements include CI/CD integration with GitHub Actions, Docker containerization, cloud deployment, streaming ingestion simulation, anomaly detection improvements, and enhanced observability and monitoring.

## Author

Hugo Batista – Data Engineer focused on analytics engineering, ELT pipelines, and AI-powered data systems.

GitHub: https://github.com/hugomoc/data-engineering-demo
