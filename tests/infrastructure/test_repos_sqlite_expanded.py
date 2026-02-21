from __future__ import annotations

import sqlite3

import pytest

from app.infrastructure.repos_sqlite import (
    PersonaRepositorySQLite,
    _execute_with_validation,
    _run_with_locked_retry,
)


def test_execute_with_validation_detects_param_mismatch() -> None:
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    with pytest.raises(ValueError):
        _execute_with_validation(cursor, "SELECT ? + ?", [1], "test.context")


def test_get_or_create_uuid_handles_absent_and_existing_rows(connection: sqlite3.Connection) -> None:
    repo = PersonaRepositorySQLite(connection)
    assert repo.get_or_create_uuid(-999) is None

    connection.execute("INSERT INTO personas (id, uuid, nombre, genero, horas_mes_min, horas_ano_min, is_active, deleted) VALUES (1, 'already', 'Ana', 'F', 1, 1, 1, 0)")
    connection.commit()

    assert repo.get_or_create_uuid(1) == "already"


def test_get_or_create_uuid_works_without_updated_at_column() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE personas (id INTEGER PRIMARY KEY, uuid TEXT, deleted INTEGER)")
    conn.execute("INSERT INTO personas (id, uuid, deleted) VALUES (1, '', 0)")
    conn.commit()

    repo = PersonaRepositorySQLite(conn)
    generated = repo.get_or_create_uuid(1)

    assert generated
    persisted = conn.execute("SELECT uuid FROM personas WHERE id = 1").fetchone()[0]
    assert persisted == generated


def test_delete_by_ids_noop_when_ids_are_empty(solicitud_repo) -> None:
    solicitud_repo.delete_by_ids([])


def test_run_with_locked_retry_retries_only_locked_operational_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}
    sleeps: list[float] = []

    def _operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise sqlite3.OperationalError("database is locked")
        return "ok"

    monkeypatch.setattr("app.infrastructure.repos_sqlite.time.sleep", lambda value: sleeps.append(value))

    result = _run_with_locked_retry(_operation, context="test.locked")

    assert result == "ok"
    assert attempts["count"] == 3
    assert sleeps == [0.05, 0.15]


def test_run_with_locked_retry_does_not_retry_non_locked_operational_error() -> None:
    def _operation() -> None:
        raise sqlite3.OperationalError("no such table")

    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        _run_with_locked_retry(_operation, context="test.non_locked")
