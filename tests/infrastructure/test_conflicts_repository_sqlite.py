from __future__ import annotations

import json
import sqlite3

import pytest

from app.infrastructure.repos_conflicts_sqlite import SQLiteConflictsRepository, _execute_with_validation


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


def test_resolve_conflict_devuelve_false_si_no_existe(connection: sqlite3.Connection) -> None:
    repository = SQLiteConflictsRepository(connection)
    assert repository.resolve_conflict(999, keep_local=True, device_id="d") is False


def test_list_conflicts_parsea_snapshots(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO conflicts (uuid, entity_type, local_snapshot_json, remote_snapshot_json, detected_at)
        VALUES ('x', 'delegadas', '{"a": 1}', '{"b": 2}', '2025-01-01T00:00:00Z')
        """
    )
    connection.commit()
    repository = SQLiteConflictsRepository(connection)

    conflictos = repository.list_conflicts()

    assert len(conflictos) == 1
    assert conflictos[0].local_snapshot == {"a": 1}
    assert conflictos[0].remote_snapshot == {"b": 2}
    assert repository.count_conflicts() == 1


def test_resolve_conflict_solicitud_remota_inserta(connection: sqlite3.Connection, persona_repo, persona_id: int) -> None:
    delegada_uuid = persona_repo.get_or_create_uuid(persona_id)
    assert delegada_uuid
    connection.execute(
        """
        INSERT INTO conflicts (uuid, entity_type, local_snapshot_json, remote_snapshot_json, detected_at)
        VALUES (?, 'solicitudes', '{}', ?, '2025-02-01T11:00:00Z')
        """,
        (
            "sol-new",
            json.dumps(
                {
                    "delegada_uuid": delegada_uuid,
                    "fecha": "2025-02-01",
                    "desde_h": "08",
                    "desde_m": "15",
                    "hasta_h": "09",
                    "hasta_m": "00",
                    "minutos_total": "45",
                    "notas": "remota",
                    "pdf_id": "pdf-z",
                }
            ),
        ),
    )
    conflict_id = connection.execute("SELECT id FROM conflicts WHERE uuid = 'sol-new'").fetchone()["id"]
    repository = SQLiteConflictsRepository(connection)

    assert repository.resolve_conflict(conflict_id, keep_local=False, device_id="x") is True
    row = connection.execute("SELECT persona_id, desde_min, hasta_min, notas, pdf_hash FROM solicitudes WHERE uuid = 'sol-new'").fetchone()
    assert row is not None
    assert row["persona_id"] == persona_id
    assert row["desde_min"] == 495
    assert row["hasta_min"] == 540
    assert row["notas"] == "remota"
    assert row["pdf_hash"] == "pdf-z"


def test_resolve_conflict_solicitud_local_actualiza_y_marca_dirty(
    connection: sqlite3.Connection, persona_repo, persona_id: int
) -> None:
    delegada_uuid = persona_repo.get_or_create_uuid(persona_id)
    connection.execute(
        """
        INSERT INTO solicitudes (uuid, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
            horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash, created_at, updated_at, source_device, deleted)
        VALUES ('sol-1', ?, '2025-01-01', '2025-01-01', 60, 120, 0, 60, NULL, 'old', NULL, 'h',
            '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z', 'old-device', 0)
        """,
        (persona_id,),
    )
    connection.execute(
        """
        INSERT INTO conflicts (uuid, entity_type, local_snapshot_json, remote_snapshot_json, detected_at)
        VALUES ('sol-1', 'solicitudes', ?, '{}', '2025-02-01T11:00:00Z')
        """,
        (
            json.dumps(
                {
                    "persona_id": persona_id,
                    "fecha_pedida": "2025-03-01",
                    "desde_min": 120,
                    "hasta_min": 180,
                    "completo": 1,
                    "horas_solicitadas_min": 60,
                    "notas": "local",
                    "pdf_hash": "hash-new",
                }
            ),
        ),
    )
    conflict_id = connection.execute("SELECT id FROM conflicts WHERE uuid = 'sol-1'").fetchone()["id"]
    repository = SQLiteConflictsRepository(connection)

    assert repository.resolve_conflict(conflict_id, keep_local=True, device_id="device-local") is True
    row = connection.execute(
        "SELECT fecha_pedida, desde_min, hasta_min, notas, source_device, completo FROM solicitudes WHERE uuid = 'sol-1'"
    ).fetchone()
    assert row["fecha_pedida"] == "2025-03-01"
    assert row["desde_min"] == 120
    assert row["hasta_min"] == 180
    assert row["notas"] == "local"
    assert row["source_device"] == "device-local"
    assert row["completo"] == 1


def test_resolve_conflict_cuadrante_actualiza_persona(
    connection: sqlite3.Connection, persona_repo, persona_id: int
) -> None:
    delegada_uuid = persona_repo.get_or_create_uuid(persona_id)
    connection.execute(
        """
        INSERT INTO conflicts (uuid, entity_type, local_snapshot_json, remote_snapshot_json, detected_at)
        VALUES ('cuad-1', 'cuadrantes', '{}', ?, '2025-02-01T11:00:00Z')
        """,
        (json.dumps({"delegada_uuid": delegada_uuid, "dia_semana": "martes", "man_h": "2", "man_m": "0", "tar_h": "3", "tar_m": "0"}),),
    )
    conflict_id = connection.execute("SELECT id FROM conflicts WHERE uuid = 'cuad-1'").fetchone()["id"]
    repository = SQLiteConflictsRepository(connection)

    assert repository.resolve_conflict(conflict_id, keep_local=False, device_id="dev") is True
    cuadrante = connection.execute("SELECT man_min, tar_min FROM cuadrantes WHERE uuid = 'cuad-1'").fetchone()
    persona = connection.execute("SELECT cuad_mar_man_min, cuad_mar_tar_min FROM personas WHERE id = ?", (persona_id,)).fetchone()
    assert cuadrante["man_min"] == 120
    assert cuadrante["tar_min"] == 180
    assert persona["cuad_mar_man_min"] == 120
    assert persona["cuad_mar_tar_min"] == 180


def test_apply_resolution_ignore_entity_desconocida(connection: sqlite3.Connection) -> None:
    repository = SQLiteConflictsRepository(connection)
    repository._apply_resolution("desconocida", "u", {}, {}, keep_local=True, device_id="d")


def test_solicitud_remota_sin_delegada_lanza_error(connection: sqlite3.Connection) -> None:
    repository = SQLiteConflictsRepository(connection)
    with pytest.raises(RuntimeError):
        repository._apply_solicitud("u", {"delegada_uuid": "inexistente"}, mark_dirty=False, remote=True, device_id="d")


def test_execute_with_validation_detecta_parametros_invalidos(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    with pytest.raises(ValueError):
        _execute_with_validation(cursor, "SELECT ?", (), "ctx")


def test_utilidades_estaticas_normalizan_y_convierten() -> None:
    assert SQLiteConflictsRepository._int_or_zero("2.9") == 2
    assert SQLiteConflictsRepository._join_minutes("1", "30") == 90
    assert SQLiteConflictsRepository._join_minutes(None, None) is None
    assert SQLiteConflictsRepository._normalize_dia("Miércoles") == "mie"
    assert SQLiteConflictsRepository._normalize_dia("nope") is None


def test_apply_cuadrante_to_persona_sale_si_no_hay_persona(connection: sqlite3.Connection) -> None:
    repository = SQLiteConflictsRepository(connection)
    repository._apply_cuadrante_to_persona("inexistente", "lun", 10, 20)
