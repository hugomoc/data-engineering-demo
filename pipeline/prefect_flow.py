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
    logger.info("Starting incremental load")

    incremental_load.main()  # MUST fully close DB inside

    logger.info("Incremental load completed")

    # safety buffer for file lock release
    time.sleep(2)


@task(name="quality-checks", retries=1)
def validate():
    logger.info("Starting quality checks")

    quality_checks.main()  # MUST be read-only + closed properly

    logger.info("Quality checks completed")

    time.sleep(1)


@task(name="dbt-run", retries=1)
def transform():
    logger.info("Starting dbt run")

    project_dir = (
        Path(__file__).resolve().parent.parent / "ecommerce_project"
    )

    env = os.environ.copy()
    env["DBT_THREADS"] = "1"

    # run dbt run
    subprocess.run(
        ["dbt", "run"],
        cwd=project_dir,
        check=True,
        env=env
    )

    # run dbt test
    subprocess.run(
        ["dbt", "test"],
        cwd=project_dir,
        check=True,
        env=env
    )

    logger.info("dbt completed")


@flow(name="ecommerce-pipeline")
def ecommerce_pipeline():

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