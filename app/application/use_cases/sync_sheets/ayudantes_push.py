from __future__ import annotations

from typing import Any

from app.application.sheets_service import SHEETS_SCHEMA
from app.application.use_cases import sync_sheets_core


def push_pdf_log(service: Any, spreadsheet: Any, last_sync_at: str | None) -> int:
    worksheet = service._get_worksheet(spreadsheet, "pdf_log")
    headers, rows = service._rows_with_index(worksheet)
    header_map = service._header_map(headers, SHEETS_SCHEMA["pdf_log"])
    remote_index = {row["pdf_id"]: row for _, row in rows if row.get("pdf_id")}
    cursor = service._connection.cursor()
    cursor.execute(
        """
        SELECT pdf_id, delegada_uuid, rango_fechas, fecha_generacion, hash, updated_at, source_device
        FROM pdf_log
        WHERE updated_at IS NOT NULL
        """
    )
    uploaded = 0
    for row in cursor.fetchall():
        if not sync_sheets_core.is_after_last_sync(row["updated_at"], last_sync_at):
            continue
        remote_row = remote_index.get(row["pdf_id"])
        remote_updated_at = sync_sheets_core.parse_iso(remote_row.get("updated_at") if remote_row else None)
        local_updated_at = sync_sheets_core.parse_iso(row["updated_at"])
        if remote_row and remote_updated_at and local_updated_at and remote_updated_at > local_updated_at:
            continue
        payload = {
            "pdf_id": row["pdf_id"],
            "delegada_uuid": row["delegada_uuid"],
            "rango_fechas": row["rango_fechas"],
            "fecha_generacion": row["fecha_generacion"],
            "hash": row["hash"],
            "updated_at": row["updated_at"],
            "source_device": row["source_device"] or service._device_id(),
        }
        if remote_row:
            if service._enable_backfill:
                row_number = remote_row["__row_number__"]
                service._update_row(worksheet, row_number, header_map, payload)
            continue
        service._append_row(worksheet, header_map, payload)
        uploaded += 1
    service._flush_write_batches(spreadsheet, worksheet)
    return uploaded


def push_config(service: Any, spreadsheet: Any, last_sync_at: str | None) -> int:
    worksheet = service._get_worksheet(spreadsheet, "config")
    headers, rows = service._rows_with_index(worksheet)
    header_map = service._header_map(headers, SHEETS_SCHEMA["config"])
    remote_index = {row["key"]: row for _, row in rows if row.get("key")}
    cursor = service._connection.cursor()
    cursor.execute(
        """
        SELECT key, value, updated_at, source_device
        FROM sync_config
        WHERE updated_at IS NOT NULL
        """
    )
    uploaded = 0
    for row in cursor.fetchall():
        if not sync_sheets_core.is_after_last_sync(row["updated_at"], last_sync_at):
            continue
        remote_row = remote_index.get(row["key"])
        remote_updated_at = sync_sheets_core.parse_iso(remote_row.get("updated_at") if remote_row else None)
        local_updated_at = sync_sheets_core.parse_iso(row["updated_at"])
        if remote_row and remote_updated_at and local_updated_at and remote_updated_at > local_updated_at:
            continue
        payload = {
            "key": row["key"],
            "value": row["value"],
            "updated_at": row["updated_at"],
            "source_device": row["source_device"] or service._device_id(),
        }
        if remote_row:
            if service._enable_backfill:
                row_number = remote_row["__row_number__"]
                service._update_row(worksheet, row_number, header_map, payload)
            continue
        service._append_row(worksheet, header_map, payload)
        uploaded += 1
    service._flush_write_batches(spreadsheet, worksheet)
    return uploaded


def push_delegadas(service: Any, spreadsheet: Any, last_sync_at: str | None) -> tuple[int, int]:
    worksheet = service._get_worksheet(spreadsheet, "delegadas")
    headers, rows = service._rows_with_index(worksheet)
    header_map = service._header_map(headers, SHEETS_SCHEMA["delegadas"])
    remote_index = service._uuid_index(rows)
    cursor = service._connection.cursor()
    cursor.execute(
        """
        SELECT id, uuid, nombre, genero, is_active, horas_mes_min, horas_ano_min,
               updated_at, source_device, deleted
        FROM personas
        WHERE updated_at IS NOT NULL
        """
    )
    uploaded = 0
    conflicts = 0
    for row in cursor.fetchall():
        if not sync_sheets_core.is_after_last_sync(row["updated_at"], last_sync_at):
            continue
        uuid_value = row["uuid"]
        remote_row = remote_index.get(uuid_value)
        remote_updated_at = sync_sheets_core.parse_iso(remote_row.get("updated_at") if remote_row else None)
        if sync_sheets_core.is_conflict(row["updated_at"], remote_updated_at, last_sync_at):
            service._store_conflict("delegadas", uuid_value, dict(row), remote_row or {})
            conflicts += 1
            continue
        payload = {
            "uuid": uuid_value,
            "nombre": row["nombre"],
            "genero": row["genero"],
            "activa": 1 if row["is_active"] else 0,
            "bolsa_mes_min": row["horas_mes_min"] or 0,
            "bolsa_anual_min": row["horas_ano_min"] or 0,
            "updated_at": row["updated_at"],
            "source_device": row["source_device"] or service._device_id(),
            "deleted": row["deleted"] or 0,
        }
        if remote_row:
            if service._enable_backfill:
                row_number = remote_row["__row_number__"]
                service._update_row(worksheet, row_number, header_map, payload)
            continue
        service._append_row(worksheet, header_map, payload)
        uploaded += 1
    service._flush_write_batches(spreadsheet, worksheet)
    return uploaded, conflicts
