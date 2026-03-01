from __future__ import annotations

import sqlite3

from app.infrastructure.migrations import run_migrations


def test_run_migrations_smoke_creates_expected_tables() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    run_migrations(connection)

    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    table_names = {row["name"] for row in cursor.fetchall()}

    expected_tables = {"personas", "solicitudes", "sync_state", "conflicts"}
    assert expected_tables.issubset(table_names)
