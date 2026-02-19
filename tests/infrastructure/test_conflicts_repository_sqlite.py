from __future__ import annotations

import json
import sqlite3

from app.infrastructure.repos_conflicts_sqlite import SQLiteConflictsRepository


def test_sqlite_conflicts_repository_resolves_local_persona_conflict(
    connection: sqlite3.Connection,
    persona_repo,
    persona_id: int,
) -> None:
    delegada_uuid = persona_repo.get_or_create_uuid(persona_id)
    assert delegada_uuid is not None

    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO conflicts (uuid, entity_type, local_snapshot_json, remote_snapshot_json, detected_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            delegada_uuid,
            "delegadas",
            json.dumps(
                {
                    "nombre": "Delegada Local",
                    "genero": "F",
                    "horas_mes_min": 700,
                    "horas_ano_min": 8000,
                    "is_active": 1,
                    "updated_at": "2025-02-01T10:00:00Z",
                    "source_device": "old-device",
                    "deleted": 0,
                }
            ),
            json.dumps({}),
            "2025-02-01T11:00:00Z",
        ),
    )
    conflict_id = int(cursor.lastrowid)
    connection.commit()

    repository = SQLiteConflictsRepository(connection)

    resolved = repository.resolve_conflict(conflict_id, keep_local=True, device_id="new-device")

    assert resolved is True
    remaining = repository.count_conflicts()
    assert remaining == 0

    persona = persona_repo.get_by_id(persona_id)
    assert persona is not None
    assert persona.nombre == "Delegada Local"

    row = connection.execute("SELECT source_device FROM personas WHERE id = ?", (persona_id,)).fetchone()
    assert row is not None
    assert row["source_device"] == "new-device"
