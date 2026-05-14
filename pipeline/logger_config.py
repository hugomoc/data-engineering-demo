import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("../pipeline.log"),
        logging.StreamHandler()
    ],
    force=True
)

# Reduce Prefect/internal HTTP noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("prefect").setLevel(logging.WARNING)

logger = logging.getLogger("pipeline")