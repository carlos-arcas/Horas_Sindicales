from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.application.sync_normalization import normalize_hhmm


def _pick_value(row: dict[str, Any], key: str | tuple[str, ...], default: Any = "") -> Any:
    if isinstance(key, tuple):
        for candidate in key:
            value = row.get(candidate)
            if value:
                return value
        return default
    return row.get(key) or default


def _coerce_str(value: Any, default: str = "") -> str:
    return value or default


def _coerce_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_fecha(value: Any) -> str:
    return normalize_date(_coerce_str(value)) or ""


def normalize_date(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def to_iso_date(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    normalized = normalize_date(text)
    if normalized:
        return normalized
    if "-" in text:
        return text
    return text


def int_or_zero(value: Any) -> int:
    try:
        if value is None or value == "":
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def split_minutes(value: Any) -> tuple[int, int]:
    minutes = int_or_zero(value)
    return minutes // 60, minutes % 60


def parse_hhmm_to_minutes(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, str) and ":" in value:
        parts = value.strip().split(":")
        if len(parts) >= 2:
            try:
                hours = int(parts[0])
                minutes = int(parts[1])
            except ValueError:
                return None
            return hours * 60 + minutes
    return None


def join_minutes(hours: Any, minutes: Any) -> int | None:
    if hours is None and minutes is None:
        return None
    return int_or_zero(hours) * 60 + int_or_zero(minutes)


def normalize_total_minutes(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int_or_zero(value)


def normalize_hm_to_minutes(hours: Any, minutes: Any) -> int | None:
    if hours is None and minutes is None:
        return None
    parsed = parse_hhmm_to_minutes(hours)
    if parsed is not None:
        return parsed
    return int_or_zero(hours) * 60 + int_or_zero(minutes)


def build_delegada_key(delegada_uuid: str | None, delegada_id: int | None) -> str | None:
    uuid_value = (delegada_uuid or "").strip()
    if uuid_value:
        return f"uuid:{uuid_value}"
    if delegada_id is None:
        return None
    return f"id:{delegada_id}"


def solicitud_dedupe_key(
    delegada_uuid: str | None,
    delegada_id: int | None,
    fecha_pedida: Any,
    completo: bool,
    horas_min: Any,
    desde_min: Any,
    hasta_min: Any,
) -> tuple[object, ...] | None:
    delegada_key = build_delegada_key(delegada_uuid, delegada_id)
    if not delegada_key or not fecha_pedida:
        return None
    minutos_total = int_or_zero(horas_min)
    if completo:
        return (delegada_key, str(fecha_pedida), True, minutos_total, None, None)
    desde_value = normalize_total_minutes(desde_min)
    hasta_value = normalize_total_minutes(hasta_min)
    return (delegada_key, str(fecha_pedida), False, minutos_total, desde_value, hasta_value)


def solicitud_dedupe_key_from_remote_row(row: dict[str, Any]) -> tuple[object, ...] | None:
    delegada_uuid = str(row.get("delegada_uuid", "")).strip() or None
    delegada_id = None
    if row.get("delegada_id") not in (None, ""):
        delegada_id = int_or_zero(row.get("delegada_id"))
    fecha_pedida = row.get("fecha") or row.get("fecha_pedida")
    completo = bool(int_or_zero(row.get("completo")))
    horas_min = row.get("minutos_total") or row.get("horas_solicitadas_min")
    desde_min = normalize_hm_to_minutes(row.get("desde_h"), row.get("desde_m"))
    hasta_min = normalize_hm_to_minutes(row.get("hasta_h"), row.get("hasta_m"))
    return solicitud_dedupe_key(delegada_uuid, delegada_id, fecha_pedida, completo, horas_min, desde_min, hasta_min)


def solicitud_dedupe_key_from_local_row(row: dict[str, Any]) -> tuple[object, ...] | None:
    return solicitud_dedupe_key(
        row.get("delegada_uuid"),
        row.get("persona_id"),
        row.get("fecha_pedida"),
        bool(row.get("completo")),
        row.get("horas_solicitadas_min"),
        row.get("desde_min"),
        row.get("hasta_min"),
    )


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_after_last_sync(updated_at: str | None, last_sync_at: str | None) -> bool:
    if not updated_at:
        return False
    if not last_sync_at:
        return True
    parsed_updated = parse_iso(updated_at)
    parsed_last = parse_iso(last_sync_at)
    if not parsed_updated or not parsed_last:
        return False
    return parsed_updated > parsed_last


def is_conflict(local_updated_at: str | None, remote_updated_at: datetime | None, last_sync_at: str | None) -> bool:
    if not local_updated_at or not remote_updated_at or not last_sync_at:
        return False
    parsed_local = parse_iso(local_updated_at)
    parsed_last = parse_iso(last_sync_at)
    if not parsed_local or not parsed_last:
        return False
    return parsed_local > parsed_last and remote_updated_at > parsed_last


def is_remote_newer(local_updated_at: str | None, remote_updated_at: datetime | None) -> bool:
    if not remote_updated_at:
        return False
    if not local_updated_at:
        return True
    parsed_local = parse_iso(local_updated_at)
    if not parsed_local:
        return True
    return remote_updated_at > parsed_local


def remote_hhmm(hours: Any, minutes: Any, full_value: Any) -> str | None:
    full_text = normalize_hhmm(str(full_value).strip()) if full_value not in (None, "") else None
    if full_text:
        return full_text
    if hours in (None, "") and minutes in (None, ""):
        return None
    return normalize_hhmm(f"{hours}:{minutes}")


def canonical_remote_solicitud_person_fields(row: dict[str, Any]) -> tuple[Any, str]:
    delegada_uuid = row.get("delegada_uuid") or ""
    if row.get("delegada_uuid") in (None, "") and row.get("delegado_uuid") not in (None, ""):
        delegada_uuid = row.get("delegado_uuid")
    delegada_nombre = row.get("delegada_nombre") or row.get("Delegada") or ""
    if row.get("delegada_nombre") in (None, ""):
        delegada_nombre = (
            row.get("Delegada") or row.get("delegado_nombre") or row.get("delegada") or row.get("delegado") or ""
        )
    return delegada_uuid, delegada_nombre


def canonical_remote_solicitud_time_parts(row: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    desde_hhmm = remote_hhmm(row.get("desde_h"), row.get("desde_m"), row.get("desde") or row.get("hora_desde"))
    hasta_hhmm = remote_hhmm(row.get("hasta_h"), row.get("hasta_m"), row.get("hasta") or row.get("hora_hasta"))
    if not desde_hhmm:
        desde_h, desde_m = "", ""
    else:
        desde_h, desde_m = (int(value) for value in desde_hhmm.split(":"))
    if not hasta_hhmm:
        hasta_h, hasta_m = "", ""
    else:
        hasta_h, hasta_m = (int(value) for value in hasta_hhmm.split(":"))
    return desde_h, desde_m, hasta_h, hasta_m


def canonical_remote_solicitud_estado(row: dict[str, Any], worksheet_name: str) -> str:
    estado = str(row.get("estado", "")).strip().lower()
    if estado:
        return estado
    if worksheet_name.strip().lower() in {"histórico", "historico"}:
        return "historico"
    return ""


def _normalize_dates(payload: dict[str, Any], row: dict[str, Any]) -> None:
    payload["fecha"] = _normalize_fecha(_pick_value(row, ("fecha", "fecha_pedida")))
    payload["created_at"] = _normalize_fecha(_pick_value(row, "created_at")) or payload["fecha"] or ""


def _normalize_numeric_fields(payload: dict[str, Any], row: dict[str, Any]) -> None:
    if row.get("minutos_total") in (None, "") and row.get("horas") not in (None, ""):
        payload["minutos_total"] = _coerce_int(row.get("horas"))
    payload["desde_h"], payload["desde_m"], payload["hasta_h"], payload["hasta_m"] = (
        canonical_remote_solicitud_time_parts(row)
    )


def _normalize_text_fields(payload: dict[str, Any], row: dict[str, Any], worksheet_name: str) -> None:
    payload["delegada_uuid"], payload["delegada_nombre"] = canonical_remote_solicitud_person_fields(row)
    payload["estado"] = canonical_remote_solicitud_estado(row, worksheet_name)


def _validate_required_fields(payload: dict[str, Any]) -> None:
    required_fields = (
        "uuid",
        "delegada_uuid",
        "delegada_nombre",
        "fecha",
        "estado",
        "created_at",
        "updated_at",
    )
    for field in required_fields:
        if payload.get(field) is None:
            payload[field] = ""


def normalize_remote_solicitud_row(row: dict[str, Any], worksheet_name: str) -> dict[str, Any]:
    field_getters: dict[str, str | tuple[str, ...]] = {
        "uuid": "uuid",
        "delegada_uuid": "delegada_uuid",
        "delegada_nombre": ("delegada_nombre", "Delegada"),
        "fecha": ("fecha", "fecha_pedida"),
        "desde": ("desde", "hora_desde"),
        "hasta": ("hasta", "hora_hasta"),
        "desde_h": "desde_h",
        "desde_m": "desde_m",
        "hasta_h": "hasta_h",
        "hasta_m": "hasta_m",
        "completo": "completo",
        "minutos_total": "minutos_total",
        "horas": "horas",
        "notas": "notas",
        "estado": "estado",
        "created_at": "created_at",
        "updated_at": "updated_at",
        "source_device": "source_device",
        "deleted": "deleted",
        "pdf_id": "pdf_id",
    }
    normalizers: dict[str, Any] = {field: _coerce_str for field in field_getters}
    payload = {
        field: normalizers[field](_pick_value(row, key))
        for field, key in field_getters.items()
    }
    _normalize_dates(payload, row)
    _normalize_numeric_fields(payload, row)
    _normalize_text_fields(payload, row, worksheet_name)
    _validate_required_fields(payload)
    return payload
