# Data Engineering Demo: Modern ELT Pipeline with dbt, Prefect & DuckDB

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Prefect](https://img.shields.io/badge/Orchestration-Prefect-purple)
![dbt](https://img.shields.io/badge/Transformations-dbt-orange)
![DuckDB](https://img.shields.io/badge/Warehouse-DuckDB-yellow)
![FastAPI](https://img.shields.io/badge/API-FastAPI-green)

---

## Highlights

* End-to-end **ELT pipeline** simulating an e-commerce data platform
* Workflow orchestration using **Prefect**
* Analytics engineering layer built with **dbt**
* Local analytical warehouse using **DuckDB**
* Incremental data ingestion with deduplication logic
* Data quality checks embedded in pipeline
* Exposed analytics through **FastAPI**
* Production-style modular project structure

---

## Overview

This project demonstrates a modern data engineering stack designed around real-world analytics workflows. It ingests raw e-commerce data, processes it through a Python-based ingestion layer, transforms it using dbt, and serves analytics-ready datasets via SQL and API endpoints.

It is designed to simulate how modern analytics platforms are built in production environments using ELT patterns.

---

## Architecture

```text id="a9v2kq"
                +----------------------+
                |   CSV Data Sources   |
                | customers / orders   |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Python Ingestion     |
                | (Incremental Loads)  |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |      DuckDB          |
                |   Raw Data Layer     |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |        dbt           |
                | Staging + Marts      |
                | Tests + Models       |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |  Analytics Outputs   |
                | SQL / API (FastAPI) |
                +----------------------+
```

---

## Project Structure

```text id="q3l8fd"
api/                  → FastAPI service
data/                 → Raw + generated datasets
pipeline/             → ETL + Prefect workflows
sql/                  → Analytical SQL queries
ecommerce_project/    → dbt project (models, tests, marts)
logs/                 → Execution and dbt logs
```

---

## Key Components

### 1. Data Ingestion (Python)

* Reads raw CSV datasets
* Generates daily incremental order files
* Tracks processed files to prevent duplication

### 2. Orchestration (Prefect)

* Automates full pipeline execution
* Manages task dependencies
* Provides logging and retry handling

### 3. Storage Layer (DuckDB)

* Lightweight analytical warehouse
* Supports fast SQL-based transformations
* Acts as central data store

### 4. Transformations (dbt)

* Staging models for raw normalization
* Mart models for business metrics
* Data tests for quality assurance
* Auto-generated documentation and lineage

### 5. Data Quality Layer

* Validates incoming datasets
* Detects missing or duplicate records
* Ensures pipeline integrity before transformations

### 6. API Layer (FastAPI)

* Exposes processed analytical data
* Enables external querying of metrics

---

## Tech Stack

* Python 3.12
* Prefect
* dbt-core
* DuckDB
* FastAPI
* SQL
* Pandas

---

## How to Run

### Install dependencies

```bash id="g8r1ab"
pip install -r requirements.txt
```

### Run pipeline

```bash id="x7m2pq"
python pipeline/prefect_flow.py
```

### Run dbt

```bash id="k9q4ld"
cd ecommerce_project
dbt run
dbt test
```

### Start API

```bash id="m2v9sd"
uvicorn api.main:app --reload
```

---

## Future Improvements

* Add CI/CD with GitHub Actions
* Containerize with Docker
* Deploy API (AWS / Render / Fly.io)
* Add real-time streaming ingestion (Kafka simulation)
* Integrate AI layer:

  * Automated insights generation
  * Anomaly detection explanations
  * Natural language data summaries
* Add data observability dashboard

---

## Author

Hugo Batista — Data Engineer focused on analytics engineering, ELT pipelines, and modern data platforms.

## GitHub: https://github.com/hugomoc

## Why this project matters

This project demonstrates production-style thinking in modern data engineering:

* Separation of ingestion, transformation, and serving layers
* Modular and testable pipeline design
* Use of analytics engineering best practices (dbt)
* Orchestration and automation (Prefect)
* Extensible architecture ready for cloud + AI enhancements
