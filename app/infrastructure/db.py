from __future__ import annotations

import sqlite3
from pathlib import Path

DB_FILENAME = "horas_sindicales.db"
DB_RUNTIME_DIR = Path("logs") / "runtime"
DEFAULT_BUSY_TIMEOUT_MS = 30000


def _default_db_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / DB_RUNTIME_DIR / DB_FILENAME


def configure_sqlite_connection(connection: sqlite3.Connection, busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS) -> None:
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")


def get_connection(
    db_path: Path | None = None,
    *,
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    check_same_thread: bool = False,
) -> sqlite3.Connection:
    path = db_path or _default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        path,
        check_same_thread=check_same_thread,
        timeout=max(1.0, busy_timeout_ms / 1000),
    )
    configure_sqlite_connection(connection, busy_timeout_ms=busy_timeout_ms)
    return connection
