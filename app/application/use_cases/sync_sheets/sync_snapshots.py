from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable


@dataclass(frozen=True)
class RemoteSolicitudRowDTO:
    row: dict[str, Any]
    uuid_value: str
    remote_updated_at: datetime | None


@dataclass(frozen=True)
class PullSignals:
    has_existing_for_empty_uuid: bool
    has_local_uuid: bool
    skip_duplicate: bool
    conflict_detected: bool
    remote_is_newer: bool
    backfill_enabled: bool
    existing_uuid: str | None


@dataclass(frozen=True)
class PullContext:
    dto: RemoteSolicitudRowDTO
    local_row: Any | None


def parse_remote_solicitud_row(
    row: dict[str, Any],
    *,
    normalize_remote_uuid: Callable[[Any], str],
    parse_iso: Callable[[Any], datetime | None],
) -> RemoteSolicitudRowDTO:
    uuid_value = normalize_remote_uuid(row.get("uuid"))
    remote_updated_at = parse_iso(row.get("updated_at")) if uuid_value else None
    return RemoteSolicitudRowDTO(row=row, uuid_value=uuid_value, remote_updated_at=remote_updated_at)


def build_pull_signals_snapshot(
    *,
    dto: RemoteSolicitudRowDTO,
    local_row: Any | None,
    existing: Any | None,
    skip_duplicate: bool,
    enable_backfill: bool,
    is_conflict: Callable[[Any, datetime | None, str | None], bool],
    is_remote_newer: Callable[[Any, datetime | None], bool],
    last_sync_at: str | None,
) -> PullSignals:
    existing_uuid = str(existing["uuid"] or "").strip() if existing is not None else None
    return PullSignals(
        has_existing_for_empty_uuid=existing is not None,
        has_local_uuid=local_row is not None,
        skip_duplicate=bool(skip_duplicate),
        conflict_detected=bool(local_row and is_conflict(local_row["updated_at"], dto.remote_updated_at, last_sync_at)),
        remote_is_newer=bool(local_row and is_remote_newer(local_row["updated_at"], dto.remote_updated_at)),
        backfill_enabled=enable_backfill,
        existing_uuid=existing_uuid,
    )


def build_pdf_log_payload(row: dict[str, Any]) -> dict[str, Any] | None:
    pdf_id = str(row.get("pdf_id", "")).strip()
    if not pdf_id:
        return None
    return {
        "pdf_id": pdf_id,
        "delegada_uuid": row.get("delegada_uuid"),
        "rango_fechas": row.get("rango_fechas"),
        "fecha_generacion": row.get("fecha_generacion"),
        "hash": row.get("hash"),
        "updated_at": row.get("updated_at"),
        "source_device": row.get("source_device"),
    }


def pdf_log_insert_values(payload: dict[str, Any]) -> tuple[Any, ...]:
    return (
        payload["pdf_id"],
        payload["delegada_uuid"],
        payload["rango_fechas"],
        payload["fecha_generacion"],
        payload["hash"],
        payload["updated_at"],
        payload["source_device"],
    )


def pdf_log_update_values(payload: dict[str, Any]) -> tuple[Any, ...]:
    return (
        payload["delegada_uuid"],
        payload["rango_fechas"],
        payload["fecha_generacion"],
        payload["hash"],
        payload["updated_at"],
        payload["source_device"],
        payload["pdf_id"],
    )


def build_local_solicitud_payload(row: Any, *, device_id: str, to_iso_date: Callable[[Any], str], split_minutes: Callable[[Any], tuple[int, int]], int_or_zero: Callable[[Any], int]) -> tuple[Any, ...]:
    desde_h, desde_m = split_minutes(row["desde_min"])
    hasta_h, hasta_m = split_minutes(row["hasta_min"])
    return (
        row["uuid"],
        row["delegada_uuid"] or "",
        row["delegada_nombre"] or "",
        to_iso_date(row["fecha_pedida"]),
        desde_h,
        desde_m,
        hasta_h,
        hasta_m,
        1 if row["completo"] else 0,
        int_or_zero(row["horas_solicitadas_min"]),
        row["notas"] or "",
        "",
        to_iso_date(row["created_at"]),
        to_iso_date(row["updated_at"]),
        row["source_device"] or device_id,
        int_or_zero(row["deleted"]),
        row["pdf_hash"] or "",
    )


def format_rango_fechas(fechas: list[str]) -> str:
    fechas_filtradas = sorted({fecha for fecha in fechas if fecha})
    if not fechas_filtradas:
        return ""
    if len(fechas_filtradas) == 1:
        return fechas_filtradas[0]
    return f"{fechas_filtradas[0]} - {fechas_filtradas[-1]}"


def normalize_dia(dia: str) -> str | None:
    value = dia.strip().lower()
    mapping = {
        "lunes": "lun",
        "martes": "mar",
        "miercoles": "mie",
        "miércoles": "mie",
        "jueves": "jue",
        "viernes": "vie",
        "sabado": "sab",
        "sábado": "sab",
        "domingo": "dom",
    }
    if value in mapping:
        return mapping[value]
    if value in {"lun", "mar", "mie", "jue", "vie", "sab", "dom"}:
        return value
    return None
