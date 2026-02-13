from __future__ import annotations

from app.infrastructure.migrations import run_data_fixups


def test_fixup_generated_promueve_importadas_y_respeta_pendientes(connection, persona_repo, persona_id) -> None:
    persona_repo.get_or_create_uuid(persona_id)
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO solicitudes (
            uuid, persona_id, fecha_solicitud, fecha_pedida, completo, horas_solicitadas_min,
            notas, generated, source_device, deleted, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "remote-1",
            persona_id,
            "2025-01-12",
            "2025-01-12",
            0,
            60,
            "importada",
            0,
            "device-remoto",
            0,
            "2025-01-12",
            "2025-01-12T10:00:00Z",
        ),
    )
    cursor.execute(
        """
        INSERT INTO solicitudes (
            uuid, persona_id, fecha_solicitud, fecha_pedida, completo, horas_solicitadas_min,
            notas, generated, source_device, deleted, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "local-pendiente",
            persona_id,
            "2025-01-13",
            "2025-01-13",
            0,
            60,
            "pendiente",
            0,
            None,
            0,
            "2025-01-13",
            "2025-01-13T10:00:00Z",
        ),
    )
    connection.commit()

    run_data_fixups(connection)
    run_data_fixups(connection)

    cursor.execute("SELECT uuid, generated FROM solicitudes ORDER BY uuid")
    rows = {row["uuid"]: row["generated"] for row in cursor.fetchall()}
    assert rows["local-pendiente"] == 0
    assert rows["remote-1"] == 1
