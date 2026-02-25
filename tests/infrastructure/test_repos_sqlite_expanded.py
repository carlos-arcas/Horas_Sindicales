from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

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


def test_run_with_locked_retry_supera_bloqueo_transitorio_de_otra_conexion(tmp_path: Path) -> None:
    db_path = tmp_path / "locks.db"
    schema_conn = sqlite3.connect(db_path)
    schema_conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, valor TEXT)")
    schema_conn.commit()
    schema_conn.close()

    lock_conn = sqlite3.connect(db_path, timeout=0.05, check_same_thread=False)
    lock_conn.execute("BEGIN EXCLUSIVE")
    lock_conn.execute("INSERT INTO demo(valor) VALUES ('lock')")

    worker_conn = sqlite3.connect(db_path, timeout=0.05)
    try:
        def _release_lock() -> None:
            time.sleep(0.02)
            lock_conn.rollback()

        release_thread = threading.Thread(target=_release_lock)
        release_thread.start()

        def _operation() -> str:
            worker_conn.execute("INSERT INTO demo(valor) VALUES ('ok')")
            worker_conn.commit()
            return "ok"

        result = _run_with_locked_retry(_operation, context="integration.transient_lock")
        release_thread.join(timeout=1)

        assert result == "ok"
        total = worker_conn.execute("SELECT COUNT(*) FROM demo WHERE valor = 'ok'").fetchone()[0]
        assert total == 1
    finally:
        worker_conn.close()
        lock_conn.close()


def test_is_locked_operational_error_detecta_mayusculas() -> None:
    from app.infrastructure.repos_sqlite import _is_locked_operational_error

    assert _is_locked_operational_error(sqlite3.OperationalError("DATABASE IS LOCKED")) is True
    assert _is_locked_operational_error(sqlite3.OperationalError("no such table")) is False


def test_run_with_locked_retry_agota_reintentos_y_relanza(monkeypatch: pytest.MonkeyPatch) -> None:
    intentos = {"n": 0}
    pausas: list[float] = []

    def _operation() -> None:
        intentos["n"] += 1
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(time, "sleep", lambda segundos: pausas.append(segundos))

    with pytest.raises(sqlite3.OperationalError, match="locked"):
        _run_with_locked_retry(_operation, context="test.locked.exhausted")

    # 3 intentos en bucle + 1 intento final fuera del bucle
    assert intentos["n"] == 4
    assert pausas == [0.05, 0.15, 0.3]
