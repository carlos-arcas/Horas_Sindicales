from __future__ import annotations

import sqlite3

import pytest

from app.infrastructure.sqlite_uow import transaccion


@pytest.fixture
def connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE ledger (id INTEGER PRIMARY KEY, balance INTEGER NOT NULL)")
    conn.execute("INSERT INTO ledger (id, balance) VALUES (1, 100), (2, 100)")
    return conn


def _balance(conn: sqlite3.Connection, row_id: int) -> int:
    row = conn.execute("SELECT balance FROM ledger WHERE id = ?", (row_id,)).fetchone()
    return int(row["balance"]) if row else 0


def test_transaccion_commit_operacion_compuesta(connection: sqlite3.Connection) -> None:
    with transaccion(connection):
        connection.execute("UPDATE ledger SET balance = balance - 20 WHERE id = 1")
        connection.execute("UPDATE ledger SET balance = balance + 20 WHERE id = 2")

    assert _balance(connection, 1) == 80
    assert _balance(connection, 2) == 120


def test_transaccion_rollback_si_hay_error(connection: sqlite3.Connection) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with transaccion(connection):
            connection.execute("UPDATE ledger SET balance = balance - 50 WHERE id = 1")
            raise RuntimeError("boom")

    assert _balance(connection, 1) == 100
    assert _balance(connection, 2) == 100


def test_transaccion_nested_savepoint_aísla_error_interno(connection: sqlite3.Connection) -> None:
    with transaccion(connection):
        connection.execute("UPDATE ledger SET balance = balance - 10 WHERE id = 1")

        try:
            with transaccion(connection):
                connection.execute("UPDATE ledger SET balance = balance + 999 WHERE id = 2")
                raise ValueError("rollback interno")
        except ValueError:
            pass

        connection.execute("UPDATE ledger SET balance = balance + 10 WHERE id = 2")

    assert _balance(connection, 1) == 90
    assert _balance(connection, 2) == 110
