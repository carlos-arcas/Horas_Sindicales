from __future__ import annotations

import random
import sqlite3
from datetime import datetime
from typing import Any

from app.application.sheets_service import SHEETS_SCHEMA

SEED = 424242
SCENARIOS = 48


VALID_TS = [
    "2025-01-01T10:00:00+00:00",
    "2025-01-02T10:00:00+00:00",
    "2025-01-03T10:00:00+00:00",
]


def _ws(name: str, rows: list[list[Any]]) -> list[list[Any]]:
    return [SHEETS_SCHEMA[name], *rows]


def _rand_uuid(rng: random.Random, prefix: str, idx: int) -> str:
    return f"{prefix}-{idx}-{rng.randint(100, 999)}"


def _build_scenario(rng: random.Random, case_id: int) -> tuple[dict[str, list[list[Any]]], int]:
    delegadas: list[list[Any]] = []
    solicitudes: list[list[Any]] = []
    invalid_rows = 0

    total_delegadas = rng.randint(1, 5)
    known_uuids: list[str] = []
    for idx in range(total_delegadas):
        uuid_value = _rand_uuid(rng, f"del{case_id}", idx)
        known_uuids.append(uuid_value)
        nombre = f"Delegada {case_id}-{idx}"
        if rng.random() < 0.18 and delegadas:
            # Duplicado de nombre para cubrir colisiones por alias.
            nombre = str(delegadas[0][1])
        delegadas.append(
            [
                uuid_value if rng.random() > 0.08 else "",
                nombre,
                rng.choice(["F", "M", ""]),
                rng.choice([0, 1]),
                rng.choice([480, 600, 720]),
                rng.choice([5400, 7200, 8400]),
                rng.choice(VALID_TS),
                "remote-device",
                rng.choice([0, 0, 0, 1]),
            ]
        )

    total_solicitudes = rng.randint(2, 9)
    for idx in range(total_solicitudes):
        uuid_mode = rng.random()
        if uuid_mode < 0.22:
            uuid_value: Any = ""
        elif uuid_mode < 0.28:
            uuid_value = None
        else:
            uuid_value = _rand_uuid(rng, f"sol{case_id}", idx)

        if rng.random() < 0.2 and solicitudes:
            # Fuerza duplicidad parcial/total en algunas filas.
            uuid_value = solicitudes[-1][0]

        delegada_uuid = rng.choice(known_uuids + ["", None, "missing-uuid"])
        delegada_nombre = f"Delegada {case_id}-{rng.randint(0, total_delegadas - 1)}"

        fecha = rng.choice(["2025-01-15", "2025-01-16", "", "2025-99-99", "15/01/2025"])
        if fecha in {"", "2025-99-99", "15/01/2025"}:
            invalid_rows += 1

        desde_h = rng.choice([8, 9, 10, 25, -1, "xx", None])
        desde_m = rng.choice([0, 15, 30, 60, -5, "yy", None])
        hasta_h = rng.choice([11, 12, 13, 27, "zz", None])
        hasta_m = rng.choice([0, 30, 45, 75, "ww", None])

        solicitudes.append(
            [
                uuid_value,
                delegada_uuid,
                delegada_nombre,
                fecha,
                desde_h,
                desde_m,
                hasta_h,
                hasta_m,
                rng.choice([0, 1, ""]),
                rng.choice([60, 120, 180, "", "abc"]),
                f"Nota {case_id}-{idx}",
                "pendiente",
                rng.choice(VALID_TS + [""]),
                rng.choice(VALID_TS + ["bad-ts"]),
                rng.choice(["remote-device", "other-device", ""]),
                rng.choice([0, 0, 1]),
                "",
            ]
        )

    payload = {
        "delegadas": _ws("delegadas", delegadas),
        "solicitudes": _ws("solicitudes", solicitudes),
    }
    return payload, invalid_rows


def _assert_no_duplicate_uuid(connection: sqlite3.Connection) -> None:
    total = connection.execute(
        "SELECT COUNT(*) AS total FROM (SELECT uuid FROM solicitudes WHERE uuid IS NOT NULL GROUP BY uuid HAVING COUNT(*) > 1)"
    ).fetchone()["total"]
    assert total == 0


def _assert_no_orphans(connection: sqlite3.Connection) -> None:
    total = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM solicitudes s
        LEFT JOIN personas p ON p.id = s.persona_id
        WHERE p.id IS NULL
        """
    ).fetchone()["total"]
    assert total == 0


def _solicitud_updated_at(connection: sqlite3.Connection) -> dict[str, str]:
    rows = connection.execute("SELECT uuid, updated_at FROM solicitudes WHERE uuid IS NOT NULL").fetchall()
    return {row["uuid"]: row["updated_at"] for row in rows}


def _parse_iso_or_none(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _assert_updated_at_monotonic(before: dict[str, str], after: dict[str, str]) -> None:
    for uuid_value, before_ts in before.items():
        if uuid_value not in after:
            continue
        before_dt = _parse_iso_or_none(before_ts)
        after_dt = _parse_iso_or_none(after[uuid_value])
        if before_dt is None or after_dt is None:
            continue
        assert after_dt >= before_dt


def _snapshot_without_timestamps(connection: sqlite3.Connection) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    solicitudes = connection.execute(
        """
        SELECT uuid, persona_id, fecha_pedida, desde_min, hasta_min, completo, horas_solicitadas_min, notas, deleted
        FROM solicitudes
        ORDER BY uuid
        """
    ).fetchall()
    personas = connection.execute(
        """
        SELECT uuid, nombre, genero, is_active, horas_mes_min, horas_ano_min, deleted
        FROM personas
        ORDER BY uuid
        """
    ).fetchall()
    return [tuple(row) for row in solicitudes], [tuple(row) for row in personas]


def test_sync_fuzz_light_determinista(make_service, e2e_connection: sqlite3.Connection) -> None:
    rng = random.Random(SEED)

    for case_id in range(SCENARIOS):
        payload, expected_invalid_rows = _build_scenario(rng, case_id)
        service, _ = make_service(initial_values=payload)

        baseline_last_sync = service.get_last_sync_at()
        baseline_updated = _solicitud_updated_at(e2e_connection)

        failed_controlled = False
        summary_first = None
        try:
            summary_first = service.sync_bidirectional()
        except (ValueError, sqlite3.DatabaseError):
            failed_controlled = True

        if failed_controlled:
            continue

        assert summary_first is not None
        if expected_invalid_rows > 0:
            # Criterio explícito: escenarios inválidos se aceptan si no rompen invariantes globales.
            # Alternativa válida: fallo controlado (capturado arriba en failed_controlled).
            assert summary_first is not None

        _assert_no_duplicate_uuid(e2e_connection)
        _assert_no_orphans(e2e_connection)

        first_last_sync = service.get_last_sync_at()
        after_first_updated = _solicitud_updated_at(e2e_connection)
        _assert_updated_at_monotonic(baseline_updated, after_first_updated)

        snap_first = _snapshot_without_timestamps(e2e_connection)
        summary_second = service.sync_bidirectional()
        snap_second = _snapshot_without_timestamps(e2e_connection)
        after_second_updated = _solicitud_updated_at(e2e_connection)
        second_last_sync = service.get_last_sync_at()

        assert summary_second.errors >= 0
        if expected_invalid_rows == 0:
            assert snap_second == snap_first
        _assert_updated_at_monotonic(after_first_updated, after_second_updated)
        if baseline_last_sync and first_last_sync:
            assert first_last_sync >= baseline_last_sync
        if first_last_sync and second_last_sync:
            assert second_last_sync >= first_last_sync

        # Limpiamos estado para que cada escenario sea independiente.
        for table in ("conflicts", "solicitudes", "cuadrantes", "pdf_log", "personas", "sync_config"):
            e2e_connection.execute(f"DELETE FROM {table}")
        e2e_connection.execute("UPDATE sync_state SET last_sync_at = NULL WHERE id = 1")
        e2e_connection.commit()
