from __future__ import annotations

import sqlite3
from copy import deepcopy

from app.application.sheets_service import SHEETS_SCHEMA
from app.application.use_cases.sync_sheets import SheetsSyncService
from app.domain.models import SheetsConfig
from app.infrastructure.migrations import run_migrations
from tests.e2e_sync.fakes import FakeSheetsConfigStore, FakeSheetsGateway, FakeSheetsRepository


BASE_TS = "2025-01-01T10:00:00+00:00"


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
            [
                [
                    "sol-1",
                    "del-1",
                    "Ana",
                    "2025-01-15",
                    9,
                    0,
                    11,
                    0,
                    0,
                    120,
                    "Nota base",
                    "pendiente",
                    BASE_TS,
                    BASE_TS,
                    "remote-device",
                    0,
                    "",
                ],
                [
                    "sol-2",
                    "del-1",
                    "Ana",
                    "2025-01-16",
                    10,
                    0,
                    12,
                    0,
                    0,
                    120,
                    "Nota base 2",
                    "pendiente",
                    BASE_TS,
                    BASE_TS,
                    "remote-device",
                    0,
                    "",
                ],
            ],
        ),
    }


def _build_service(initial_values: dict[str, list[list[object]]]) -> tuple[sqlite3.Connection, SheetsSyncService, FakeSheetsGateway]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    gateway = FakeSheetsGateway(initial_values=deepcopy(initial_values))
    service = SheetsSyncService(
        connection=conn,
        config_store=FakeSheetsConfigStore(
            SheetsConfig(
                spreadsheet_id="sheet-prop",
                credentials_path="/tmp/fake-credentials.json",
                device_id="device-prop",
            )
        ),
        client=gateway,
        repository=FakeSheetsRepository(),
    )
    return conn, service, gateway


def _table_snapshot(conn: sqlite3.Connection, table: str, without_timestamps: bool = False) -> list[tuple[object, ...]]:
    columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]
    if without_timestamps:
        columns = [
            name
            for name in columns
            if name not in {"created_at", "updated_at", "detected_at", "last_sync_at"}
        ]
    selected = ", ".join(columns)
    order_by = ", ".join(columns)
    rows = conn.execute(f"SELECT {selected} FROM {table} ORDER BY {order_by}").fetchall()
    return [tuple(row[col] for col in columns) for row in rows]


def _system_snapshot(conn: sqlite3.Connection, without_timestamps: bool = False) -> dict[str, list[tuple[object, ...]]]:
    return {
        "personas": _table_snapshot(conn, "personas", without_timestamps=without_timestamps),
        "solicitudes": _table_snapshot(conn, "solicitudes", without_timestamps=without_timestamps),
        "cuadrantes": _table_snapshot(conn, "cuadrantes", without_timestamps=without_timestamps),
        "conflicts": _table_snapshot(conn, "conflicts", without_timestamps=without_timestamps),
    }


def _business_projection_snapshot(conn: sqlite3.Connection) -> dict[str, list[tuple[object, ...]]]:
    personas = conn.execute(
        "SELECT uuid, nombre, genero, is_active, horas_mes_min, horas_ano_min, deleted FROM personas ORDER BY uuid"
    ).fetchall()
    solicitudes = conn.execute(
        """
        SELECT uuid, persona_id, fecha_pedida, desde_min, hasta_min, completo,
               horas_solicitadas_min, notas, deleted
        FROM solicitudes
        ORDER BY uuid
        """
    ).fetchall()
    conflicts = conn.execute(
        "SELECT entity_type, uuid FROM conflicts ORDER BY entity_type, uuid"
    ).fetchall()
    return {
        "personas": [tuple(row) for row in personas],
        "solicitudes": [tuple(row) for row in solicitudes],
        "conflicts": [tuple(row) for row in conflicts],
    }


def test_sync_es_fuertemente_idempotente_en_repeticiones() -> None:
    conn, service, _ = _build_service(_base_payload())

    first = service.sync_bidirectional()
    stable_snapshots = [_system_snapshot(conn, without_timestamps=True)]
    conflict_counts = [conn.execute("SELECT COUNT(*) AS total FROM conflicts").fetchone()["total"]]
    solicitud_counts = [conn.execute("SELECT COUNT(*) AS total FROM solicitudes").fetchone()["total"]]

    for _ in range(4):
        summary = service.sync_bidirectional()
        stable_snapshots.append(_system_snapshot(conn, without_timestamps=True))
        conflict_counts.append(conn.execute("SELECT COUNT(*) AS total FROM conflicts").fetchone()["total"])
        solicitud_counts.append(conn.execute("SELECT COUNT(*) AS total FROM solicitudes").fetchone()["total"])
        assert summary.inserted_local == 0
        assert summary.inserted_remote == 0

    assert first.inserted_local >= 1
    assert all(snapshot == stable_snapshots[0] for snapshot in stable_snapshots[1:])
    assert all(count == conflict_counts[0] for count in conflict_counts[1:])
    assert all(count == solicitud_counts[0] for count in solicitud_counts[1:])


def test_sync_es_monotono_en_timestamps_y_cardinalidad() -> None:
    conn, service, gateway = _build_service(_base_payload())

    last_sync_values: list[str] = []
    max_updated_at_values: list[str] = []
    solicitud_counts: list[int] = []

    for iteration in range(4):
        if iteration == 2:
            gateway._values["solicitudes"].append(
                [
                    "sol-3",
                    "del-1",
                    "Ana",
                    "2025-01-17",
                    8,
                    0,
                    10,
                    0,
                    0,
                    120,
                    "Nota agregada",
                    "pendiente",
                    BASE_TS,
                    "2025-01-02T10:00:00+00:00",
                    "remote-device",
                    0,
                    "",
                ]
            )

        service.sync_bidirectional()
        last_sync_values.append(service.get_last_sync_at() or "")
        max_updated_at_values.append(
            conn.execute("SELECT COALESCE(MAX(updated_at), '') AS max_updated_at FROM solicitudes").fetchone()["max_updated_at"]
        )
        solicitud_counts.append(conn.execute("SELECT COUNT(*) AS total FROM solicitudes").fetchone()["total"])

    assert all(curr >= prev for prev, curr in zip(last_sync_values, last_sync_values[1:]))
    assert all(curr >= prev for prev, curr in zip(max_updated_at_values, max_updated_at_values[1:]))
    assert all(curr >= prev for prev, curr in zip(solicitud_counts, solicitud_counts[1:]))


def test_pull_es_invariante_ante_orden_de_filas_remotas() -> None:
    base_rows = _base_payload()["solicitudes"][1:]
    ordered_payload = _base_payload()
    reversed_payload = _base_payload()
    reversed_payload["solicitudes"] = [SHEETS_SCHEMA["solicitudes"], *list(reversed(base_rows))]

    conn_ordered, service_ordered, _ = _build_service(ordered_payload)
    conn_reversed, service_reversed, _ = _build_service(reversed_payload)

    service_ordered.sync_bidirectional()
    service_reversed.sync_bidirectional()

    assert _business_projection_snapshot(conn_ordered) == _business_projection_snapshot(conn_reversed)


def test_pull_ignora_duplicados_remotos_y_no_duplica_local() -> None:
    payload = _base_payload()
    payload["solicitudes"].append(payload["solicitudes"][1].copy())
    conn, service, _ = _build_service(payload)

    summary = service.sync_bidirectional()

    total = conn.execute("SELECT COUNT(*) AS total FROM solicitudes").fetchone()["total"]
    duplicated = conn.execute(
        "SELECT COUNT(*) AS total FROM (SELECT uuid FROM solicitudes GROUP BY uuid HAVING COUNT(*) > 1)"
    ).fetchone()["total"]
    assert total == 2
    assert duplicated == 0
    assert summary.conflicts_detected == 0


def test_pull_hace_rollback_total_si_hay_fallo_en_medio_del_plan() -> None:
    conn, service, _ = _build_service(_base_payload())
    conn.execute(
        """
        CREATE TRIGGER abort_second_solicitud
        BEFORE INSERT ON solicitudes
        WHEN NEW.uuid = 'sol-2'
        BEGIN
            SELECT RAISE(ABORT, 'fallo simulado a mitad de plan pull');
        END;
        """
    )
    conn.commit()

    try:
        service.sync_bidirectional()
        raise AssertionError("El sync debía fallar para validar rollback de savepoint")
    except sqlite3.DatabaseError:
        pass

    assert conn.execute("SELECT COUNT(*) AS total FROM solicitudes").fetchone()["total"] == 0
    assert conn.execute("SELECT COUNT(*) AS total FROM conflicts").fetchone()["total"] == 0
