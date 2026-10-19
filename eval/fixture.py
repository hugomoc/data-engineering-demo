"""Share the disposable dbt fixture between numeric tests and evaluation."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

from scripts.build_ci_fixture_db import build_fixture


ROOT = Path(__file__).resolve().parents[1]


def find_dbt():
    sibling = Path(sys.executable).parent / "dbt"
    return str(sibling) if sibling.is_file() else shutil.which("dbt")


def build_database(directory):
    executable = find_dbt()
    if not executable:
        raise FileNotFoundError("dbt is unavailable; install dbt-duckdb for fixture evaluation")
    directory = Path(directory).resolve()
    database = directory / "agent-eval.duckdb"
    build_fixture(database)
    project = ROOT / "ecommerce_project"
    environment = dict(os.environ, DUCKDB_PATH=str(database),
        DBT_PROFILES_DIR=str(project), DBT_SEND_ANONYMOUS_USAGE_STATS="false")
    environment["PYTHONPATH"] = os.pathsep.join((
        str(ROOT / "scripts" / "offline_guard"), str(ROOT),
        environment.get("PYTHONPATH", ""),
    ))
    result = subprocess.run(
        [executable, "build", "--project-dir", str(project), "--profiles-dir", str(project),
         "--target-path", str(directory / "target"), "--log-path", str(directory / "logs")],
        cwd=project, env=environment, capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError("Synthetic dbt build failed:\n" + result.stdout + result.stderr)
    return database
