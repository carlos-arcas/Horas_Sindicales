from __future__ import annotations

import sqlite3

import pytest

from app.application.delegada_resolution import get_or_resolve_delegada_uuid


@pytest.fixture
def local_people_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE personas (id INTEGER PRIMARY KEY, uuid TEXT, nombre TEXT)")
    conn.execute("INSERT INTO personas (uuid, nombre) VALUES ('uuid-1', 'Ana María')")
    conn.execute("INSERT INTO personas (uuid, nombre) VALUES ('uuid-2', 'Lola Perez')")
    conn.commit()
    return conn


def test_resolve_delegada_uuid_prefers_existing_uuid(local_people_connection: sqlite3.Connection) -> None:
    resolved = get_or_resolve_delegada_uuid(local_people_connection, "uuid-1", "nombre ignorado")
    assert resolved == "uuid-1"


def test_resolve_delegada_uuid_falls_back_to_normalized_name(local_people_connection: sqlite3.Connection) -> None:
    resolved = get_or_resolve_delegada_uuid(local_people_connection, "missing", "  lola   perez  ")
    assert resolved == "uuid-2"


def test_resolve_delegada_uuid_uses_delegadas_table_when_present(local_people_connection: sqlite3.Connection) -> None:
    local_people_connection.execute("CREATE TABLE delegadas (uuid TEXT, nombre TEXT)")
    local_people_connection.execute("INSERT INTO delegadas (uuid, nombre) VALUES ('uuid-delegadas', 'María Ruiz')")
    local_people_connection.commit()

    resolved = get_or_resolve_delegada_uuid(local_people_connection, None, "mARÍA   rUIZ")
    assert resolved == "uuid-delegadas"


def test_resolve_delegada_uuid_returns_none_when_not_found(local_people_connection: sqlite3.Connection) -> None:
    assert get_or_resolve_delegada_uuid(local_people_connection, None, "") is None
    assert get_or_resolve_delegada_uuid(local_people_connection, None, "No Existe") is None
