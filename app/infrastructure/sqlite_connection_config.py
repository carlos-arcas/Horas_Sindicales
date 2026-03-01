from __future__ import annotations

import logging
import sqlite3

DEFAULT_BUSY_TIMEOUT_MS = 30000

logger = logging.getLogger(__name__)


def configurar_conexion(conn: sqlite3.Connection, busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS) -> None:
    """Aplica PRAGMAs base para conexiones SQLite del proyecto."""
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.DatabaseError:
        logger.debug("sqlite_journal_mode_wal_not_supported", exc_info=True)
