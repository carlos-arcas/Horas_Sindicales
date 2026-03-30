from __future__ import annotations

import sqlite3

from app.application.use_cases.sync_sheets.orquestador_persistencia import (
    OrquestadorPersistenciaSync,
)


class _ClientStub:
    def __init__(self, values: list[list[str]]) -> None:
        self._values = values

    def read_all_values(self, worksheet_name: str) -> list[list[str]]:
        assert worksheet_name == "delegadas"
        return self._values


class _ServiceStub(OrquestadorPersistenciaSync):
    def __init__(self, connection: sqlite3.Connection, values: list[list[str]]) -> None:
        self._connection = connection
        self._client = _ClientStub(values)
        self._delegadas_nombre_por_uuid_cache = None


def _build_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE personas (id INTEGER PRIMARY KEY, uuid TEXT, nombre TEXT)")
    connection.execute(
        "INSERT INTO personas (id, uuid, nombre) VALUES (2, 'b49c3014-2136-4a95-acf3-50e125eea7c8', 'Dora Inés Solano Franco')"
    )
    connection.commit()
    return connection


def test_resolver_persona_para_solicitud_recupera_nombre_desde_delegadas() -> None:
    connection = _build_connection()
    values = [
        ["uuid", "nombre"],
        ["43b3150d-115e-49b6-a863-74f03865c059", "Dora Inés Solano Franco"],
    ]
    service = _ServiceStub(connection, values)

    persona_id = service._resolver_persona_para_solicitud(
        {"delegada_uuid": "43b3150d-115e-49b6-a863-74f03865c059", "delegada_nombre": ""},
        "sol-1",
    )

    assert persona_id == 2


def test_resolver_persona_para_solicitud_devuelve_none_si_uuid_no_tiene_nombre_remoto() -> None:
    connection = _build_connection()
    service = _ServiceStub(connection, [["uuid", "nombre"]])

    persona_id = service._resolver_persona_para_solicitud(
        {"delegada_uuid": "43b3150d-115e-49b6-a863-74f03865c059", "delegada_nombre": ""},
        "sol-2",
    )

    assert persona_id is None
