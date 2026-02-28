from __future__ import annotations

import json
from typing import Any, Callable

from app.application.use_cases.sync_sheets.sync_sheets_helpers import execute_with_validation


def insert_persona_from_remote(connection: Any, uuid_value: str, row: dict[str, Any], now_iso: Callable[[], str]) -> None:
    cursor = connection.cursor()
    execute_with_validation(
        cursor,
        """
        INSERT INTO personas (
            uuid, nombre, genero, horas_mes_min, horas_ano_min, horas_jornada_defecto_min, is_active,
            cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
            cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
            cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
            cuad_dom_man_min, cuad_dom_tar_min,
            updated_at, source_device, deleted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uuid_value,
            row.get("nombre"),
            row.get("genero"),
            _int_or_zero(row.get("bolsa_mes_min")),
            _int_or_zero(row.get("bolsa_anual_min")),
            0,
            1 if _int_or_zero(row.get("activa")) else 0,
            0,0,0,0,0,0,0,0,0,0,0,0,0,0,
            row.get("updated_at") or now_iso(),
            row.get("source_device"),
            _int_or_zero(row.get("deleted")),
        ),
        "personas.insert_remote",
    )


def update_persona_from_remote(connection: Any, persona_id: int, row: dict[str, Any], now_iso: Callable[[], str]) -> None:
    cursor = connection.cursor()
    deleted = _int_or_zero(row.get("deleted"))
    execute_with_validation(
        cursor,
        """
        UPDATE personas
        SET nombre = ?, genero = ?, horas_mes_min = ?, horas_ano_min = ?, is_active = ?,
            updated_at = ?, source_device = ?, deleted = ?
        WHERE id = ?
        """,
        (
            row.get("nombre"),
            row.get("genero"),
            _int_or_zero(row.get("bolsa_mes_min")),
            _int_or_zero(row.get("bolsa_anual_min")),
            0 if deleted else (1 if _int_or_zero(row.get("activa")) else 0),
            row.get("updated_at") or now_iso(),
            row.get("source_device"),
            deleted,
            persona_id,
        ),
        "personas.update_remote",
    )


def execute_insert_solicitud(connection: Any, payload: tuple[Any, ...]) -> None:
    execute_with_validation(
        connection.cursor(),
        """
        INSERT INTO solicitudes (
            uuid, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
            horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash,
            generated, created_at, updated_at, source_device, deleted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
        "solicitudes.insert_remote",
    )


def execute_update_solicitud(connection: Any, payload: tuple[Any, ...]) -> None:
    execute_with_validation(
        connection.cursor(),
        """
        UPDATE solicitudes
        SET persona_id = ?, fecha_pedida = ?, desde_min = ?, hasta_min = ?, completo = ?,
            horas_solicitadas_min = ?, notas = ?, pdf_hash = ?, created_at = ?, updated_at = ?,
            source_device = ?, deleted = ?, generated = 1
        WHERE id = ?
        """,
        payload,
        "solicitudes.update_remote",
    )


def backfill_uuid(connection: Any, table_name: str, record_id: int, uuid_value: str, now_iso: Callable[[], str]) -> None:
    allowed_tables = {"personas", "solicitudes", "cuadrantes"}
    if table_name not in allowed_tables:
        raise ValueError(f"table_name no soportada para backfill_uuid: {table_name}")
    connection.cursor().execute(
        f"UPDATE {table_name} SET uuid = ?, updated_at = ? WHERE id = ?",
        (uuid_value, now_iso(), record_id),
    )


def store_conflict(connection: Any, uuid_value: str, entity_type: str, local_snapshot: dict[str, Any], remote_snapshot: dict[str, Any], now_iso: Callable[[], str]) -> None:
    connection.cursor().execute(
        """
        INSERT INTO conflicts (uuid, entity_type, local_snapshot_json, remote_snapshot_json, detected_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (uuid_value, entity_type, json.dumps(local_snapshot, ensure_ascii=False), json.dumps(remote_snapshot, ensure_ascii=False), now_iso()),
    )


def _int_or_zero(value: Any) -> int:
    try:
        if value in (None, ""):
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def find_solicitud_by_composite_key(connection: Any, row: dict[str, Any], persona_id: int | None) -> Any | None:
    if persona_id is None:
        return None
    from app.application.use_cases import sync_sheets_core
    from app.application.sync_normalization import normalize_hhmm, solicitud_unique_key

    delegada_uuid = str(row.get("delegada_uuid", "")).strip() or None
    fecha = sync_sheets_core.normalize_date(row.get("fecha"))
    completo = bool(sync_sheets_core.int_or_zero(row.get("completo")))
    desde = normalize_hhmm(f"{sync_sheets_core.int_or_zero(row.get('desde_h')):02d}:{sync_sheets_core.int_or_zero(row.get('desde_m')):02d}")
    hasta = normalize_hhmm(f"{sync_sheets_core.int_or_zero(row.get('hasta_h')):02d}:{sync_sheets_core.int_or_zero(row.get('hasta_m')):02d}")
    key = solicitud_unique_key(delegada_uuid, fecha, completo, desde, hasta)
    if key is None:
        return None
    desde_min = sync_sheets_core.parse_hhmm_to_minutes(desde)
    hasta_min = sync_sheets_core.parse_hhmm_to_minutes(hasta)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, uuid, persona_id, fecha_pedida, desde_min, hasta_min, completo,
               horas_solicitadas_min, notas, created_at, updated_at, source_device, deleted, pdf_hash
        FROM solicitudes
        WHERE persona_id = ? AND fecha_pedida = ? AND completo = ?
          AND (desde_min IS ? OR desde_min = ?) AND (hasta_min IS ? OR hasta_min = ?)
          AND (deleted = 0 OR deleted IS NULL)
        LIMIT 1
        """,
        (persona_id, key[1], 1 if key[2] else 0, desde_min, desde_min, hasta_min, hasta_min),
    )
    return cursor.fetchone()


def is_duplicate_local_solicitud(connection: Any, key: tuple[object, ...], exclude_uuid: str | None = None) -> bool:
    from app.application.use_cases import sync_sheets_core

    delegada_key, fecha_pedida, _, _, _, _ = key
    if not delegada_key or not fecha_pedida:
        return False
    cursor = connection.cursor()
    query = (
        """
        SELECT s.uuid, s.persona_id, p.uuid AS delegada_uuid, s.fecha_pedida,
               s.desde_min, s.hasta_min, s.completo, s.horas_solicitadas_min
        FROM solicitudes s
        JOIN personas p ON p.id = s.persona_id
        WHERE {delegada_filter}
          AND s.fecha_pedida = ?
          AND (s.deleted = 0 OR s.deleted IS NULL)
        """
    )
    if str(delegada_key).startswith("uuid:"):
        cursor.execute(query.format(delegada_filter="p.uuid = ?"), (str(delegada_key).removeprefix("uuid:"), fecha_pedida))
    elif str(delegada_key).startswith("id:"):
        persona_id = _int_or_zero(str(delegada_key).removeprefix("id:"))
        cursor.execute(query.format(delegada_filter="s.persona_id = ?"), (persona_id, fecha_pedida))
    else:
        return False
    for row in cursor.fetchall():
        if exclude_uuid and row["uuid"] == exclude_uuid:
            continue
        if sync_sheets_core.solicitud_dedupe_key_from_local_row(dict(row)) == key:
            return True
    return False
