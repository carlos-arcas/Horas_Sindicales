from __future__ import annotations

import contextlib
import sqlite3
import uuid
from collections.abc import Iterator


@contextlib.contextmanager
def transaccion(connection: sqlite3.Connection) -> Iterator[None]:
    """Gestiona transacciones SQLite con soporte de anidamiento vía SAVEPOINT."""
    if connection.in_transaction:
        savepoint_name = f"sp_{uuid.uuid4().hex}"
        connection.execute(f"SAVEPOINT {savepoint_name}")
        try:
            yield
            connection.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        except Exception:
            connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            connection.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            raise
        return

    connection.execute("BEGIN")
    try:
        yield
        connection.commit()
    except Exception:
        connection.rollback()
        raise
