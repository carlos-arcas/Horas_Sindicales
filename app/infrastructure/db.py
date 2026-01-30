from __future__ import annotations

import sqlite3
from pathlib import Path

DB_FILENAME = "horas_sindicales.db"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or Path(DB_FILENAME)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection
