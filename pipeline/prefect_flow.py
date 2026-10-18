"""Prefect orchestration for the ecommerce analytics pipeline.

The flow models the production order of operations: ingest new source data,
validate the raw fact table, then let dbt build and test the analytics layer.
DuckDB permits one writer at a time, so each task closes its connection before
the next task starts and dbt is run with a single thread.
"""

import incremental_load
import quality_checks
import subprocess
import os
import time

from pathlib import Path
from prefect import flow, task
from logger_config import logger


@task(name="incremental-load", retries=0, retry_delay_seconds=5)
def load():
    """Load new CSV extracts into the DuckDB source tables."""

    logger.info("Starting incremental load")

    incremental_load.main()  # MUST fully close DB inside

    logger.info("Incremental load completed")

    # safety buffer for file lock release
    time.sleep(2)


@task(name="quality-checks", retries=1)
def validate():
    """Run lightweight source-table quality checks before dbt transforms."""

    logger.info("Starting quality checks")

    quality_checks.main()  # MUST be read-only + closed properly

    logger.info("Quality checks completed")

    time.sleep(1)


@task(name="dbt-run", retries=1)
def transform():
    """Build and test the dbt analytics models after ingestion succeeds."""

    logger.info("Starting dbt run")

    project_dir = (
        Path(__file__).resolve().parent.parent / "ecommerce_project"
    )

    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = str(project_dir)
    # Keep dbt single-threaded to avoid concurrent DuckDB writer conflicts.
    env["DBT_THREADS"] = "1"

    # Build models and test them in dependency order.
    subprocess.run(
        ["dbt", "build"],
        cwd=project_dir,
        check=True,
        env=env
    )

    logger.info("dbt completed")


@flow(name="ecommerce-pipeline")
def ecommerce_pipeline():
    """Orchestrate ingestion, validation, and dbt transformation."""

    logger.info("Pipeline started")

    load()       # STEP 1
    validate()   # STEP 2
    transform()  # STEP 3 (dbt only now touches DB)

    logger.info("Pipeline finished successfully")

if __name__ == "__main__":
    ecommerce_pipeline.serve(
        name="daily-ecommerce-pipeline",
        cron="0 18 * * *",  # every day at 6PM UTC/11AM PT 
       
        
    )
