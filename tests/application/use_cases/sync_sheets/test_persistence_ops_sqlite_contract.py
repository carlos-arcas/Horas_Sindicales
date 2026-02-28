from __future__ import annotations

import json

from app.application.use_cases.sync_sheets import persistence_ops


FIXED_NOW = "2026-03-01T09:30:00+00:00"


def _insert_persona(connection, *, uuid: str | None, nombre: str = "Ana") -> int:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO personas (uuid, nombre, genero, horas_mes_min, horas_ano_min, is_active, updated_at, source_device, deleted)
        VALUES (?, ?, 'F', 600, 7200, 1, '2026-01-01T00:00:00+00:00', 'device-test', 0)
        """,
        (uuid if uuid else None, nombre),
    )
    return int(cursor.lastrowid)


def _insert_solicitud(connection, *, uuid: str, persona_id: int, fecha: str = "2026-02-10", desde: int = 540, hasta: int = 600, deleted: int = 0) -> int:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO solicitudes (
            uuid, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
            horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash,
            generated, created_at, updated_at, source_device, deleted
        ) VALUES (?, ?, ?, ?, ?, ?, 0, 60, NULL, 'nota', NULL, 'hash', 1, '2026-02-01', '2026-02-01T00:00:00+00:00', 'device-test', ?)
        """,
        (uuid, persona_id, fecha, fecha, desde, hasta, deleted),
    )
    return int(cursor.lastrowid)


def test_execute_insert_solicitud_respeta_orden_de_parametros(connection) -> None:
    persona_id = _insert_persona(connection, uuid="delegada-1")
    payload = (
        "sol-1", persona_id, "2026-02-01", "2026-02-15", 480, 540, 0,
        55, "obs-a", "nota-a", "/tmp/a.pdf", "hash-a",
        1, "2026-02-01T08:00:00+00:00", "2026-02-01T09:00:00+00:00", "dev-a", 0,
    )

    persistence_ops.execute_insert_solicitud(connection, payload)

    row = connection.execute("SELECT * FROM solicitudes WHERE uuid = 'sol-1'").fetchone()
    assert row["persona_id"] == persona_id
    assert row["fecha_solicitud"] == "2026-02-01"
    assert row["fecha_pedida"] == "2026-02-15"
    assert row["desde_min"] == 480
    assert row["hasta_min"] == 540
    assert row["horas_solicitadas_min"] == 55
    assert row["notas"] == "nota-a"
    assert row["pdf_hash"] == "hash-a"


def test_execute_insert_solicitud_persiste_campos_de_auditoria(connection) -> None:
    persona_id = _insert_persona(connection, uuid="delegada-2")
    payload = (
        "sol-2", persona_id, "2026-02-03", "2026-02-03", 600, 660, 1,
        60, "obs-b", "nota-b", "/tmp/b.pdf", "hash-b",
        1, "2026-02-03T10:00:00+00:00", "2026-02-03T11:00:00+00:00", "dev-b", 1,
    )

    persistence_ops.execute_insert_solicitud(connection, payload)

    row = connection.execute("SELECT generated, created_at, updated_at, source_device, deleted FROM solicitudes WHERE uuid = 'sol-2'").fetchone()
    assert tuple(row) == (1, "2026-02-03T10:00:00+00:00", "2026-02-03T11:00:00+00:00", "dev-b", 1)


def test_execute_update_solicitud_respeta_orden_de_parametros(connection) -> None:
    persona_a = _insert_persona(connection, uuid="delegada-a")
    persona_b = _insert_persona(connection, uuid="delegada-b", nombre="Bea")
    solicitud_id = _insert_solicitud(connection, uuid="sol-upd", persona_id=persona_a)
    payload = (
        persona_b, "2026-04-10", 300, 360, 0,
        90, "nota-upd", "hash-upd", "2026-04-01T08:00:00+00:00", "2026-04-01T09:00:00+00:00",
        "dev-upd", 1, solicitud_id,
    )

    persistence_ops.execute_update_solicitud(connection, payload)

    row = connection.execute("SELECT persona_id, fecha_pedida, desde_min, hasta_min, horas_solicitadas_min, notas, pdf_hash, created_at, updated_at, source_device, deleted, generated FROM solicitudes WHERE id = ?", (solicitud_id,)).fetchone()
    assert tuple(row) == (
        persona_b, "2026-04-10", 300, 360, 90, "nota-upd", "hash-upd",
        "2026-04-01T08:00:00+00:00", "2026-04-01T09:00:00+00:00", "dev-upd", 1, 1,
    )


def test_execute_update_solicitud_solo_actualiza_registro_objetivo(connection) -> None:
    persona_id = _insert_persona(connection, uuid="delegada-3")
    target_id = _insert_solicitud(connection, uuid="sol-target", persona_id=persona_id)
    other_id = _insert_solicitud(connection, uuid="sol-other", persona_id=persona_id)

    payload = (persona_id, "2026-05-01", 100, 200, 0, 100, "nota-target", "hash-target", "2026-05-01", "2026-05-01", "dev", 0, target_id)
    persistence_ops.execute_update_solicitud(connection, payload)

    updated = connection.execute("SELECT notas FROM solicitudes WHERE id = ?", (target_id,)).fetchone()["notas"]
    untouched = connection.execute("SELECT notas FROM solicitudes WHERE id = ?", (other_id,)).fetchone()["notas"]
    assert updated == "nota-target"
    assert untouched == "nota"


def test_backfill_uuid_actualiza_solo_el_registro_objetivo(connection) -> None:
    first_id = _insert_persona(connection, uuid=None)
    second_id = _insert_persona(connection, uuid=None, nombre="Bea")

    persistence_ops.backfill_uuid(connection, "personas", first_id, "uuid-backfilled", lambda: FIXED_NOW)

    first = connection.execute("SELECT uuid, updated_at FROM personas WHERE id = ?", (first_id,)).fetchone()
    second = connection.execute("SELECT uuid, updated_at FROM personas WHERE id = ?", (second_id,)).fetchone()
    assert tuple(first) == ("uuid-backfilled", FIXED_NOW)
    assert second["uuid"] in (None, "")


def test_backfill_uuid_rechaza_tabla_no_soportada(connection) -> None:
    _insert_persona(connection, uuid="x")

    try:
        persistence_ops.backfill_uuid(connection, "conflicts", 1, "uuid-x", lambda: FIXED_NOW)
        raised = False
    except ValueError:
        raised = True

    assert raised is True


def test_store_conflict_inserta_payload_json_esperado(connection) -> None:
    local = {"uuid": "sol-10", "notas": "local"}
    remote = {"uuid": "sol-10", "notas": "remote"}

    persistence_ops.store_conflict(connection, "sol-10", "solicitudes", local, remote, lambda: FIXED_NOW)

    row = connection.execute("SELECT uuid, entity_type, local_snapshot_json, remote_snapshot_json, detected_at FROM conflicts WHERE uuid = 'sol-10'").fetchone()
    assert row["entity_type"] == "solicitudes"
    assert json.loads(row["local_snapshot_json"]) == local
    assert json.loads(row["remote_snapshot_json"]) == remote
    assert row["detected_at"] == FIXED_NOW


def test_store_conflict_no_rompe_integridad_si_uuid_no_existe(connection) -> None:
    persistence_ops.store_conflict(
        connection,
        "uuid-inexistente",
        "solicitudes",
        {"a": 1},
        {"b": 2},
        lambda: FIXED_NOW,
    )

    total = connection.execute("SELECT COUNT(*) AS total FROM conflicts WHERE uuid = 'uuid-inexistente'").fetchone()["total"]
    assert total == 1


def test_dedupe_local_detecta_duplicado_por_uuid(connection) -> None:
    persona_id = _insert_persona(connection, uuid="delegada-dup")
    _insert_solicitud(connection, uuid="sol-a", persona_id=persona_id, fecha="2026-07-01", desde=540, hasta=600)
    key = ("uuid:delegada-dup", "2026-07-01", False, 60, 540, 600)

    assert persistence_ops.is_duplicate_local_solicitud(connection, key) is True


def test_dedupe_local_detecta_duplicado_por_persona_id(connection) -> None:
    persona_id = _insert_persona(connection, uuid=None, nombre="IdOnly")
    _insert_solicitud(connection, uuid="sol-b", persona_id=persona_id, fecha="2026-07-02", desde=600, hasta=660)
    key = (f"id:{persona_id}", "2026-07-02", False, 60, 600, 660)

    assert persistence_ops.is_duplicate_local_solicitud(connection, key) is True


def test_dedupe_local_excluye_uuid_indicado(connection) -> None:
    persona_id = _insert_persona(connection, uuid="delegada-ex")
    _insert_solicitud(connection, uuid="sol-ex", persona_id=persona_id, fecha="2026-07-03", desde=660, hasta=720)
    key = ("uuid:delegada-ex", "2026-07-03", False, 60, 660, 720)

    assert persistence_ops.is_duplicate_local_solicitud(connection, key, exclude_uuid="sol-ex") is False


def test_dedupe_local_no_marca_falso_positivo_por_horario_distinto(connection) -> None:
    persona_id = _insert_persona(connection, uuid="delegada-ok")
    _insert_solicitud(connection, uuid="sol-ok", persona_id=persona_id, fecha="2026-07-04", desde=480, hasta=540)
    key = ("uuid:delegada-ok", "2026-07-04", False, 60, 500, 560)

    assert persistence_ops.is_duplicate_local_solicitud(connection, key) is False


def test_dedupe_local_ignora_registros_soft_deleted(connection) -> None:
    persona_id = _insert_persona(connection, uuid="delegada-del")
    _insert_solicitud(connection, uuid="sol-del", persona_id=persona_id, fecha="2026-07-05", desde=540, hasta=600, deleted=1)
    key = ("uuid:delegada-del", "2026-07-05", False, 60, 540, 600)

    assert persistence_ops.is_duplicate_local_solicitud(connection, key) is False
