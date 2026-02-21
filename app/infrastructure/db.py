from __future__ import annotations

import sqlite3
from pathlib import Path

DB_FILENAME = "horas_sindicales.db"
DB_RUNTIME_DIR = Path("logs") / "runtime"


def _default_db_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / DB_RUNTIME_DIR / DB_FILENAME


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or _default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection
