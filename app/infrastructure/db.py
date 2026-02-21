from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from app.infrastructure.local_config import resolve_appdata_dir

DB_FILENAME = "horas_sindicales.db"


def _default_db_path() -> Path:
    env_path = os.environ.get("HORAS_DB_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return resolve_appdata_dir() / "data" / DB_FILENAME


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or _default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection
