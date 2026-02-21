from __future__ import annotations

import sqlite3

from app.infrastructure.db import configure_sqlite_connection, get_connection


def test_get_connection_applies_pragmas(tmp_path) -> None:
    db_path = tmp_path / "test.db"

    connection = get_connection(db_path, busy_timeout_ms=4321)
    try:
        row = connection.execute("PRAGMA journal_mode").fetchone()
        assert row is not None
        assert str(row[0]).lower() == "wal"

        row = connection.execute("PRAGMA synchronous").fetchone()
        assert row is not None
        assert int(row[0]) == 1  # NORMAL

        row = connection.execute("PRAGMA busy_timeout").fetchone()
        assert row is not None
        assert int(row[0]) == 4321
    finally:
        connection.close()


def test_configure_sqlite_connection_sets_row_factory() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        assert connection.row_factory is None
        configure_sqlite_connection(connection)
        assert connection.row_factory is sqlite3.Row
    finally:
        connection.close()
