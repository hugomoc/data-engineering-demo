"""Shared logger configuration for pipeline scripts and Prefect tasks."""

import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "logs" / "pipeline.log"),
        logging.StreamHandler()
    ],
    force=True
)

# Reduce Prefect/internal HTTP noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("prefect").setLevel(logging.WARNING)

logger = logging.getLogger("pipeline")
