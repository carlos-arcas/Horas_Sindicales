from __future__ import annotations

from datetime import datetime
from typing import Any

from app.application.use_cases import sync_sheets_core


def _campo(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return default


def limpiar_texto(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def valor_normalizado(value: Any) -> str:
    return str(value or "").strip()


def uuid_o_none(value: Any) -> str | None:
    normalized = valor_normalizado(value)
    return normalized or None


def es_fila_vacia(row: dict[str, Any], campos: tuple[str, ...]) -> bool:
    return all(not valor_normalizado(row.get(campo)) for campo in campos)


def resolver_delegada_uuid(row: dict[str, Any]) -> str:
    return (
        valor_normalizado(row.get("delegada_uuid"))
        or valor_normalizado(row.get("delegado_uuid"))
        or valor_normalizado(row.get("persona_uuid"))
    )


def resolver_delegada_nombre(row: dict[str, Any]) -> str:
    for key in ("delegada_nombre", "Delegada", "delegado_nombre", "nombre"):
        value = limpiar_texto(row.get(key))
        if value:
            return value
    return ""


def normalizar_fecha(value: Any) -> str:
    return sync_sheets_core.to_iso_date(value)


def remote_hhmm_desde_fila(row: dict[str, Any], prefix: str) -> str | None:
    return sync_sheets_core.remote_hhmm(
        row.get(f"{prefix}_h"),
        row.get(f"{prefix}_m"),
        row.get(prefix),
    )


def hhmm_a_componentes(value: Any) -> tuple[int | str, int | str]:
    normalized = sync_sheets_core.normalize_hhmm(str(value).strip()) if value not in (None, "") else None
    if not normalized:
        return "", ""
    hours, minutes = normalized.split(":")
    return int(hours), int(minutes)


def obtener_minutos_totales(row: dict[str, Any]) -> int:
    return sync_sheets_core.int_or_zero(row.get("horas") or row.get("minutos_total"))


def payload_remoto_solicitud(remote_row: dict[str, Any]) -> tuple[Any, ...]:
    desde_hhmm = remote_row.get("desde") or remote_hhmm_desde_fila(remote_row, "desde")
    hasta_hhmm = remote_row.get("hasta") or remote_hhmm_desde_fila(remote_row, "hasta")
    desde_h, desde_m = hhmm_a_componentes(desde_hhmm)
    hasta_h, hasta_m = hhmm_a_componentes(hasta_hhmm)
    return (
        valor_normalizado(remote_row.get("uuid")),
        resolver_delegada_uuid(remote_row),
        resolver_delegada_nombre(remote_row),
        normalizar_fecha(remote_row.get("fecha") or remote_row.get("fecha_pedida")),
        desde_h,
        desde_m,
        hasta_h,
        hasta_m,
        sync_sheets_core.int_or_zero(remote_row.get("completo")),
        obtener_minutos_totales(remote_row),
        valor_normalizado(remote_row.get("notas")),
        valor_normalizado(remote_row.get("estado")),
        normalizar_fecha(remote_row.get("created_at") or remote_row.get("fecha")),
        normalizar_fecha(remote_row.get("updated_at")),
        valor_normalizado(remote_row.get("source_device")),
        sync_sheets_core.int_or_zero(remote_row.get("deleted")),
        valor_normalizado(remote_row.get("pdf_id")),
    )


def valores_distintos(local: Any, remote: Any) -> bool:
    return valor_normalizado(local) != valor_normalizado(remote)


def diff_campos(local: dict[str, Any], remote: dict[str, Any], campos: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(campo for campo in campos if valores_distintos(local.get(campo), remote.get(campo)))


def validar_shape_minimo(row: dict[str, Any], requeridos: tuple[str, ...]) -> tuple[bool, str | None]:
    faltantes = [campo for campo in requeridos if not valor_normalizado(row.get(campo))]
    if faltantes:
        return False, f"Campos requeridos ausentes: {', '.join(faltantes)}"
    return True, None


def debe_omitir_por_last_sync(updated_at: str | None, last_sync_at: str | None) -> bool:
    if not last_sync_at:
        return False
    return not sync_sheets_core.is_after_last_sync(updated_at, last_sync_at)


def normalizar_updated_at(row: dict[str, Any], fallback_iso: str) -> str:
    updated = valor_normalizado(row.get("updated_at"))
    return updated or fallback_iso


def conflicto_por_divergencia(local: dict[str, Any], remote: dict[str, Any], campos: tuple[str, ...]) -> bool:
    return bool(diff_campos(local, remote, campos))


def resolver_persona_accion(
    persona_uuid: str | None,
    nombre: str,
    by_uuid: dict[str, Any] | None,
    by_nombre: dict[str, Any] | None,
) -> dict[str, Any]:
    if persona_uuid and by_uuid:
        return {"accion": "usar_uuid", "uuid": _campo(by_uuid, "uuid")}
    if persona_uuid and by_nombre:
        existing_uuid = valor_normalizado(_campo(by_nombre, "uuid"))
        if existing_uuid and existing_uuid != persona_uuid:
            return {"accion": "colision_nombre", "uuid": existing_uuid, "nombre": nombre}
        if not existing_uuid:
            return {"accion": "asignar_uuid_por_nombre", "uuid": persona_uuid, "id": _campo(by_nombre, "id")}
        return {"accion": "usar_nombre", "uuid": existing_uuid}
    if persona_uuid:
        return {"accion": "insertar_uuid", "uuid": persona_uuid}
    if by_nombre:
        return {"accion": "usar_nombre", "uuid": _campo(by_nombre, "uuid")}
    return {"accion": "insertar_generado", "uuid": None}


def requiere_backfill_uuid(enable_backfill: bool, original_uuid: Any, persona_uuid: str | None) -> bool:
    return bool(enable_backfill and not valor_normalizado(original_uuid) and persona_uuid)


def fecha_es_valida(fecha: Any) -> bool:
    value = valor_normalizado(fecha)
    if not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False
