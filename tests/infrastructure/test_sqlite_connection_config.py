from __future__ import annotations

import sqlite3

from app.infrastructure.configuracion_conexion_sqlite import configurar_conexion


def test_configurar_conexion_habilita_foreign_keys() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        configurar_conexion(connection)
        row = connection.execute("PRAGMA foreign_keys").fetchone()
        assert row is not None
        assert int(row[0]) == 1
    finally:
        connection.close()


def test_configurar_conexion_configura_busy_timeout() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        configurar_conexion(connection)
        row = connection.execute("PRAGMA busy_timeout").fetchone()
        assert row is not None
        assert int(row[0]) > 0
    finally:
        connection.close()
