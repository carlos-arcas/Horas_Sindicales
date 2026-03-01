from __future__ import annotations

from app.infrastructure import db


def test_get_connection_enables_foreign_keys_with_in_memory_connection(monkeypatch) -> None:
    original_connect = db.sqlite3.connect

    def connect_in_memory(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original_connect(":memory:", **kwargs)

    monkeypatch.setattr(db.sqlite3, "connect", connect_in_memory)

    connection = db.get_connection()
    try:
        row = connection.execute("PRAGMA foreign_keys").fetchone()
        assert row is not None
        assert int(row[0]) == 1
    finally:
        connection.close()
