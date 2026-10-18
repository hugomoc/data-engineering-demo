"""Block network access in Python test/dbt processes and their subprocesses."""

import os
from pathlib import Path
import sys


os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "false"
os.environ["DO_NOT_TRACK"] = "1"
for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY"):
    os.environ.pop(name, None)

DEMO_DATABASE = Path(__file__).resolve().parents[2] / "ecommerce_project" / "dev.duckdb"


def offline_audit(event, arguments):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        raise RuntimeError("Network access is disabled for offline validation")
    if event == "open" and isinstance(arguments[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(arguments[0])).resolve()
        if path == DEMO_DATABASE or str(path).startswith(str(DEMO_DATABASE) + "."):
            raise RuntimeError("The demo database is excluded from offline validation")


sys.addaudithook(offline_audit)
