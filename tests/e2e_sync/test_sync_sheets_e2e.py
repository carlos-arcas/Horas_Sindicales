from __future__ import annotations

import sqlite3

from app.application.sheets_service import SHEETS_SCHEMA


BASE_TS = "2025-01-01T10:00:00+00:00"
NEWER_TS = "2025-01-02T10:00:00+00:00"
OLDER_TS = "2025-01-01T09:00:00+00:00"


def _worksheet_with_rows(name: str, rows: list[list[object]]) -> list[list[object]]:
    return [SHEETS_SCHEMA[name], *rows]


def _base_payload() -> dict[str, list[list[object]]]:
    return {
        "delegadas": _worksheet_with_rows(
            "delegadas",
            [["del-1", "Ana", "F", 1, 600, 7200, BASE_TS, "remote-device", 0]],
        ),
        "solicitudes": _worksheet_with_rows(
            "solicitudes",
            [["sol-1", "del-1", "Ana", "2025-01-15", 9, 0, 11, 0, 0, 120, "Nota inicial", "pendiente", BASE_TS, BASE_TS, "remote-device", 0, ""]],
        ),
    }


def _assert_business_invariants(connection: sqlite3.Connection) -> None:
    dup_count = connection.execute(
        "SELECT COUNT(*) AS total FROM (SELECT uuid FROM solicitudes WHERE uuid IS NOT NULL GROUP BY uuid HAVING COUNT(*) > 1)"
    ).fetchone()["total"]
    assert dup_count == 0

    orphan_count = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM solicitudes s
        LEFT JOIN personas p ON p.id = s.persona_id
        WHERE p.id IS NULL
        """
    ).fetchone()["total"]
    assert orphan_count == 0


def test_sync_crea_registros_nuevos(make_service, e2e_connection: sqlite3.Connection) -> None:
    service, _ = make_service(initial_values=_base_payload())

    summary = service.sync_bidirectional()

    assert summary.inserted_local == 2
    assert summary.conflicts_detected == 0
    assert summary.duplicates_skipped == 0
    total = e2e_connection.execute("SELECT COUNT(*) AS total FROM solicitudes").fetchone()["total"]
    assert total == 1
    _assert_business_invariants(e2e_connection)


def test_sync_actualiza_registros_existentes(make_service, e2e_connection: sqlite3.Connection) -> None:
    service, _ = make_service(
        initial_values={
            **_base_payload(),
            "solicitudes": _worksheet_with_rows(
                "solicitudes",
                [["sol-1", "del-1", "Ana", "2025-01-15", 9, 0, 11, 0, 0, 120, "Nota remota", "pendiente", BASE_TS, NEWER_TS, "remote-device", 0, ""]],
            ),
        }
    )

    e2e_connection.execute(
        """
        INSERT INTO personas (uuid, nombre, genero, is_active, horas_mes_min, horas_ano_min, updated_at, source_device, deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("del-1", "Ana", "F", 1, 600, 7200, "2024-12-30T00:00:00+00:00", "local-device", 0),
    )
    persona_id = e2e_connection.execute("SELECT id FROM personas WHERE uuid = 'del-1'").fetchone()["id"]
    e2e_connection.execute(
        """
        INSERT INTO solicitudes (uuid, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                                 horas_solicitadas_min, notas, created_at, updated_at, source_device, deleted, generated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("sol-1", persona_id, "2025-01-15", "2025-01-15", 540, 660, 0, 120, "Nota local", BASE_TS, OLDER_TS, "local-device", 0, 1),
    )
    e2e_connection.commit()

    before = e2e_connection.execute(
        "SELECT fecha_pedida, desde_min, hasta_min, horas_solicitadas_min, notas, updated_at FROM solicitudes WHERE uuid = 'sol-1'"
    ).fetchone()

    summary = service.sync_bidirectional()

    after = e2e_connection.execute(
        "SELECT fecha_pedida, desde_min, hasta_min, horas_solicitadas_min, notas, updated_at FROM solicitudes WHERE uuid = 'sol-1'"
    ).fetchone()
    assert summary.inserted_local >= 1
    assert after["notas"] == "Nota remota"
    assert after["fecha_pedida"] == before["fecha_pedida"]
    assert after["desde_min"] == before["desde_min"]
    assert after["hasta_min"] == before["hasta_min"]
    assert after["horas_solicitadas_min"] == before["horas_solicitadas_min"]
    assert after["updated_at"] >= before["updated_at"]
    dup = e2e_connection.execute("SELECT COUNT(*) AS total FROM solicitudes WHERE uuid = 'sol-1'").fetchone()["total"]
    assert dup == 1
    _assert_business_invariants(e2e_connection)


def test_sync_idempotente(make_service, e2e_connection: sqlite3.Connection) -> None:
    service, _ = make_service(initial_values=_base_payload())

    first = service.sync_bidirectional()
    first_last_sync = service.get_last_sync_at()
    second = service.sync_bidirectional()
    second_last_sync = service.get_last_sync_at()

    assert first.inserted_local == 2
    assert second.inserted_local == 0
    assert second.inserted_remote == 0
    assert second.conflicts_detected == 0
    assert second.downloaded == 0
    assert second.uploaded == 0
    assert second.errors == 0
    assert first_last_sync is not None
    assert second_last_sync is not None
    assert second_last_sync >= first_last_sync
    _assert_business_invariants(e2e_connection)


def test_sync_detecta_conflicto_divergente(make_service, e2e_connection: sqlite3.Connection) -> None:
    service, _ = make_service(initial_values=_base_payload())

    e2e_connection.execute(
        """
        INSERT INTO personas (uuid, nombre, genero, is_active, horas_mes_min, horas_ano_min, updated_at, source_device, deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("del-1", "Ana", "F", 1, 600, 7200, "2024-12-30T00:00:00+00:00", "local-device", 0),
    )
    persona_id = e2e_connection.execute("SELECT id FROM personas WHERE uuid = 'del-1'").fetchone()["id"]
    e2e_connection.execute(
        """
        INSERT INTO solicitudes (uuid, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
                                 horas_solicitadas_min, notas, created_at, updated_at, source_device, deleted, generated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("sol-1", persona_id, "2025-01-15", "2025-01-15", 540, 660, 0, 120, "Valor local", BASE_TS, NEWER_TS, "local-device", 0, 1),
    )
    e2e_connection.execute("UPDATE sync_state SET last_sync_at = ? WHERE id = 1", ("2024-12-31T00:00:00+00:00",))
    e2e_connection.commit()

    summary = service.sync_bidirectional()

    conflict_count = e2e_connection.execute("SELECT COUNT(*) AS total FROM conflicts WHERE entity_type = 'solicitudes'").fetchone()["total"]
    local_note = e2e_connection.execute("SELECT notas FROM solicitudes WHERE uuid = 'sol-1'").fetchone()["notas"]
    assert summary.conflicts_detected >= 1
    assert conflict_count >= 1
    assert local_note == "Valor local"
    _assert_business_invariants(e2e_connection)


def test_sync_rate_limit_retry(make_service, e2e_connection: sqlite3.Connection) -> None:
    service, fake_gateway = make_service(initial_values=_base_payload(), rate_limit_failures={"solicitudes": 1})

    summary = service.sync_bidirectional()

    assert summary.inserted_local == 2
    assert summary.conflicts_detected == 0
    assert fake_gateway.rate_limit_retries == 1
    _assert_business_invariants(e2e_connection)


def test_sync_no_corrompe_db_si_falla_parcialmente(make_service, e2e_connection: sqlite3.Connection) -> None:
    payload = {
        "delegadas": _worksheet_with_rows(
            "delegadas",
            [["del-1", "Ana", "F", 1, 600, 7200, BASE_TS, "remote-device", 0]],
        ),
        "solicitudes": _worksheet_with_rows(
            "solicitudes",
            [
                ["sol-ok", "del-1", "Ana", "2025-01-15", 9, 0, 11, 0, 0, 120, "Nota ok", "pendiente", BASE_TS, BASE_TS, "remote-device", 0, ""],
                ["sol-fail", "del-1", "Ana", "2025-01-16", 10, 0, 12, 0, 0, 120, "Nota fail", "pendiente", BASE_TS, BASE_TS, "remote-device", 0, ""],
            ],
        ),
    }
    service, _ = make_service(initial_values=payload)
    e2e_connection.execute(
        """
        CREATE TRIGGER fail_on_sol_fail
        BEFORE INSERT ON solicitudes
        WHEN NEW.uuid = 'sol-fail'
        BEGIN
            SELECT RAISE(ABORT, 'fallo simulado a mitad de procesamiento');
        END;
        """
    )
    e2e_connection.commit()

    try:
        service.sync_bidirectional()
        raise AssertionError("El sync debía fallar para probar rollback transaccional")
    except sqlite3.DatabaseError:
        pass

    inserted = e2e_connection.execute("SELECT COUNT(*) AS total FROM solicitudes").fetchone()["total"]
    assert inserted == 0
    _assert_business_invariants(e2e_connection)
