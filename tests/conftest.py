"""Offline defaults also reach dbt and generator subprocesses."""

import os
from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "offline_guard"
runpy.run_path(str(GUARD / "sitecustomize.py"))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONPATH"] = os.pathsep.join(
    (str(GUARD), str(ROOT), os.environ.get("PYTHONPATH", ""))
)
