from __future__ import annotations

import sqlite3
from pathlib import Path

DB_FILENAME = "horas_sindicales.db"


def _default_db_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / DB_FILENAME


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or _default_db_path()
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection
