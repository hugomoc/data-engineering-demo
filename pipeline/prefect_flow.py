from prefect import flow, task

import incremental_load
import quality_checks
import run_queries

from logger_config import logger


@task(
    name="incremental-load",
    retries=2,
    retry_delay_seconds=5
)
def load():

    logger.info("Starting incremental load task")

    incremental_load.main()

    logger.info("Incremental load task completed")


@task(
    name="quality-checks",
    retries=1
)
def validate():

    logger.info("Starting quality checks task")

    quality_checks.main()

    logger.info("Quality checks task completed")


@task(
    name="run-transformations",
    retries=1
)
def transform():

    logger.info("Starting transformation task")

    run_queries.main()

    logger.info("Transformation task completed")


@flow(name="ecommerce-pipeline")
def ecommerce_pipeline():

    logger.info("Pipeline started")

    load()

    validate()

    transform()

    logger.info("Pipeline finished successfully")


if __name__ == "__main__":

    ecommerce_pipeline()