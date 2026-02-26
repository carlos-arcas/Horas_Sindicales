from __future__ import annotations

import sqlite3

from app.infrastructure.repos_sqlite import PersonaRepositorySQLite


def test_persona_repository_sets_sqlite_runtime_pragmas() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        PersonaRepositorySQLite(connection)
        busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()
        assert busy_timeout is not None
        assert int(busy_timeout[0]) == 30000

        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()
        assert journal_mode is not None
        assert str(journal_mode[0]).lower() == "memory"
    finally:
        connection.close()
