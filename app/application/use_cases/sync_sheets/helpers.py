from __future__ import annotations

import logging
from typing import Any

from app.domain.sync_models import SyncExecutionPlan, SyncFieldDiff, SyncPlanItem

logger = logging.getLogger(__name__)


def build_solicitudes_sync_plan(
    service: Any, spreadsheet: Any, canonical_header: list[str]
) -> SyncExecutionPlan:
    worksheet = service._get_worksheet(spreadsheet, "solicitudes")
    headers, rows = service._rows_with_index(worksheet)
    remote_index = service._uuid_index(rows)
    last_sync_at = service._get_last_sync_at()
    cursor = service._connection.cursor()
    cursor.execute(
        """
        SELECT s.id, s.uuid, s.persona_id, s.fecha_pedida, s.desde_min, s.hasta_min,
               s.completo, s.horas_solicitadas_min, s.notas, s.created_at, s.updated_at,
               s.source_device, s.deleted, s.pdf_hash,
               p.uuid AS delegada_uuid, p.nombre AS delegada_nombre
        FROM solicitudes s
        JOIN personas p ON p.id = s.persona_id
        WHERE s.updated_at IS NOT NULL
        """
    )
    to_create: list[SyncPlanItem] = []
    to_update: list[SyncPlanItem] = []
    unchanged: list[SyncPlanItem] = []
    conflicts: list[SyncPlanItem] = []
    errors: list[str] = []
    values: list[tuple[Any, ...]] = [tuple(canonical_header)]
    seen_uuids: set[str] = set()

    for row in cursor.fetchall():
        plan_action = _build_solicitud_plan_for_local_row(
            service,
            row,
            remote_index,
            last_sync_at,
            canonical_header,
            values,
            errors,
        )
        if plan_action is None:
            continue
        seen_uuids.add(plan_action.uuid)
        if plan_action.action == "create":
            to_create.append(plan_action)
        elif plan_action.action == "update":
            to_update.append(plan_action)
        elif plan_action.action == "unchanged":
            unchanged.append(plan_action)
        elif plan_action.action == "conflict":
            conflicts.append(plan_action)

    for _, remote_row in rows:
        remote_uuid = str(remote_row.get("uuid", "")).strip()
        if remote_uuid and remote_uuid not in seen_uuids:
            values.append(service._remote_solicitud_payload(remote_row))

    return SyncExecutionPlan(
        generated_at=service._now_iso(),
        worksheet="solicitudes",
        to_create=tuple(to_create),
        to_update=tuple(to_update),
        unchanged=tuple(unchanged),
        conflicts=tuple(conflicts),
        potential_errors=tuple(errors),
        values_matrix=tuple(values),
    )


def _build_solicitud_plan_for_local_row(
    service: Any,
    row: Any,
    remote_index: dict[str, dict[str, Any]],
    last_sync_at: str | None,
    canonical_header: list[str],
    values: list[tuple[Any, ...]],
    errors: list[str],
) -> SyncPlanItem | None:
    if last_sync_at and not service._is_after_last_sync(row["updated_at"], last_sync_at):
        return None
    uuid_value = str(row["uuid"] or "").strip()
    if not uuid_value:
        errors.append("Solicitud sin UUID: no puede sincronizarse.")
        return None
    remote_row = remote_index.get(uuid_value)
    remote_updated_at = service._parse_iso(remote_row.get("updated_at") if remote_row else None)
    if service._is_conflict(row["updated_at"], remote_updated_at, last_sync_at):
        return SyncPlanItem(uuid=uuid_value, action="conflict", reason="Cambios locales y remotos desde última sync.")
    payload = service._local_solicitud_payload(row)
    values.append(payload)
    if remote_row is None:
        return SyncPlanItem(uuid=uuid_value, action="create", reason="Nuevo registro")
    diffs = _build_solicitud_diffs(canonical_header, service._remote_solicitud_payload(remote_row), payload)
    if diffs:
        return SyncPlanItem(uuid=uuid_value, action="update", diffs=tuple(diffs))
    return SyncPlanItem(uuid=uuid_value, action="unchanged", reason="Sin cambios")


def _build_solicitud_diffs(
    canonical_header: list[str], remote_payload: tuple[Any, ...], local_payload: tuple[Any, ...]
) -> list[SyncFieldDiff]:
    diffs: list[SyncFieldDiff] = []
    for idx, field in enumerate(canonical_header):
        current_value = str(remote_payload[idx])
        new_value = str(local_payload[idx])
        if current_value != new_value:
            diffs.append(SyncFieldDiff(field=field, current_value=current_value, new_value=new_value))
    return diffs


def sync_local_cuadrantes_from_personas(service: Any) -> None:
    cursor = service._connection.cursor()
    cursor.execute("PRAGMA table_info(personas)")
    persona_columns = {row[1] for row in cursor.fetchall()}
    has_updated_at = "updated_at" in persona_columns
    cursor.execute("SELECT uuid, id FROM personas")
    personas = cursor.fetchall()
    for persona in personas:
        persona_uuid = persona["uuid"]
        if not persona_uuid:
            persona_uuid = service._generate_uuid()
            now_iso = service._now_iso()
            if has_updated_at:
                cursor.execute(
                    "UPDATE personas SET uuid = ?, updated_at = ? WHERE id = ?",
                    (persona_uuid, now_iso, persona["id"]),
                )
            else:
                cursor.execute(
                    "UPDATE personas SET uuid = ? WHERE id = ?",
                    (persona_uuid, persona["id"]),
                )
            logger.warning(
                "Persona sin uuid encontrada (id=%s). Se generó un uuid nuevo para sincronización.",
                persona["id"],
            )
        cursor.execute(
            """
            SELECT uuid, dia_semana, man_min, tar_min, updated_at FROM cuadrantes WHERE delegada_uuid = ?
            """,
            (persona_uuid,),
        )
        existing = {row["dia_semana"]: row for row in cursor.fetchall()}
        for dia in ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]:
            man_min = _get_persona_minutes(cursor, persona["id"], dia, "man")
            tar_min = _get_persona_minutes(cursor, persona["id"], dia, "tar")
            existing_row = existing.get(dia)
            if existing_row:
                if (
                    existing_row["man_min"] == man_min
                    and existing_row["tar_min"] == tar_min
                    and existing_row["updated_at"]
                ):
                    continue
                cursor.execute(
                    """
                    UPDATE cuadrantes
                    SET man_min = ?, tar_min = ?, updated_at = ?
                    WHERE uuid = ?
                    """,
                    (man_min, tar_min, service._now_iso(), existing_row["uuid"]),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO cuadrantes (uuid, delegada_uuid, dia_semana, man_min, tar_min, updated_at, deleted)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                    """,
                    (service._generate_uuid(), persona_uuid, dia, man_min, tar_min, service._now_iso()),
                )
    service._connection.commit()


def _get_persona_minutes(cursor: Any, persona_id: int, dia: str, segmento: str) -> int:
    cursor.execute(
        f"SELECT cuad_{dia}_{segmento}_min AS value FROM personas WHERE id = ?",
        (persona_id,),
    )
    row = cursor.fetchone()
    return row["value"] if row and row["value"] is not None else 0


def extraer_datos_delegada(fila_remota: dict[str, Any]) -> tuple[str, str]:
    uuid_delegada = str(fila_remota.get("delegada_uuid") or "").strip()
    nombre_raw = fila_remota.get("delegada_nombre") or fila_remota.get("Delegada") or ""
    nombre_delegada = " ".join(str(nombre_raw).split())
    return uuid_delegada, nombre_delegada


def normalizar_fechas_solicitud(
    fila_remota: dict[str, Any],
    funcion_normalizar_fecha: Any,
) -> tuple[str | None, str | None]:
    fecha_solicitud = funcion_normalizar_fecha(fila_remota.get("fecha") or fila_remota.get("fecha_pedida"))
    fecha_creacion = funcion_normalizar_fecha(fila_remota.get("created_at")) or fecha_solicitud
    return fecha_solicitud, fecha_creacion


def calcular_bloque_horario_solicitud(fila_remota: dict[str, Any], funcion_unir_minutos: Any) -> tuple[int, int]:
    desde_min = funcion_unir_minutos(fila_remota.get("desde_h"), fila_remota.get("desde_m"))
    hasta_min = funcion_unir_minutos(fila_remota.get("hasta_h"), fila_remota.get("hasta_m"))
    return desde_min, hasta_min


def construir_payload_insercion_solicitud(
    uuid_solicitud: str,
    persona_id: int,
    fila_remota: dict[str, Any],
    fecha_solicitud: str,
    fecha_creacion: str,
    desde_min: int,
    hasta_min: int,
    funcion_entero: Any,
    funcion_ahora_iso: Any,
) -> tuple[Any, ...]:
    return (
        uuid_solicitud,
        persona_id,
        fecha_creacion,
        fecha_solicitud,
        desde_min,
        hasta_min,
        1 if funcion_entero(fila_remota.get("completo")) else 0,
        funcion_entero(fila_remota.get("minutos_total") or fila_remota.get("horas")),
        None,
        fila_remota.get("notas") or "",
        None,
        fila_remota.get("pdf_id"),
        1,
        fecha_creacion,
        fila_remota.get("updated_at") or funcion_ahora_iso(),
        fila_remota.get("source_device"),
        funcion_entero(fila_remota.get("deleted")),
    )


def construir_payload_actualizacion_solicitud(
    solicitud_id: int,
    persona_id: int,
    fila_remota: dict[str, Any],
    fecha_solicitud: str,
    fecha_creacion: str,
    desde_min: int,
    hasta_min: int,
    funcion_entero: Any,
    funcion_ahora_iso: Any,
) -> tuple[Any, ...]:
    return (
        persona_id,
        fecha_solicitud,
        desde_min,
        hasta_min,
        1 if funcion_entero(fila_remota.get("completo")) else 0,
        funcion_entero(fila_remota.get("minutos_total") or fila_remota.get("horas")),
        fila_remota.get("notas") or "",
        fila_remota.get("pdf_id"),
        fecha_creacion,
        fila_remota.get("updated_at") or funcion_ahora_iso(),
        fila_remota.get("source_device"),
        funcion_entero(fila_remota.get("deleted")),
        solicitud_id,
    )
