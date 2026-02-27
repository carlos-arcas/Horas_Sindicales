from __future__ import annotations

from typing import Any, Callable


def apply_mark_dirty(data: dict[str, Any], mark_dirty: bool, device_id: str, now_iso: str) -> dict[str, Any]:
    if not mark_dirty:
        return data
    updated = dict(data)
    updated["updated_at"] = now_iso
    updated["source_device"] = device_id
    return updated


def build_persona_data_remote(snapshot: dict[str, Any], int_or_zero: Callable[[Any], int], now_iso: str) -> dict[str, Any]:
    return {
        "nombre": snapshot.get("nombre"),
        "genero": snapshot.get("genero"),
        "horas_mes_min": int_or_zero(snapshot.get("bolsa_mes_min")),
        "horas_ano_min": int_or_zero(snapshot.get("bolsa_anual_min")),
        "is_active": 0 if int_or_zero(snapshot.get("deleted")) else (1 if int_or_zero(snapshot.get("activa")) else 0),
        "updated_at": snapshot.get("updated_at") or now_iso,
        "source_device": snapshot.get("source_device"),
        "deleted": int_or_zero(snapshot.get("deleted")),
    }


def build_persona_data_local(snapshot: dict[str, Any], int_or_zero: Callable[[Any], int], now_iso: str) -> dict[str, Any]:
    return {
        "nombre": snapshot.get("nombre"),
        "genero": snapshot.get("genero"),
        "horas_mes_min": int_or_zero(snapshot.get("horas_mes_min")),
        "horas_ano_min": int_or_zero(snapshot.get("horas_ano_min")),
        "is_active": 1 if int_or_zero(snapshot.get("is_active", 1)) else 0,
        "updated_at": snapshot.get("updated_at") or now_iso,
        "source_device": snapshot.get("source_device"),
        "deleted": int_or_zero(snapshot.get("deleted")),
    }


def build_persona_cuad_fields(snapshot: dict[str, Any], int_or_zero: Callable[[Any], int]) -> dict[str, int]:
    keys = [
        "cuad_lun_man_min",
        "cuad_lun_tar_min",
        "cuad_mar_man_min",
        "cuad_mar_tar_min",
        "cuad_mie_man_min",
        "cuad_mie_tar_min",
        "cuad_jue_man_min",
        "cuad_jue_tar_min",
        "cuad_vie_man_min",
        "cuad_vie_tar_min",
        "cuad_sab_man_min",
        "cuad_sab_tar_min",
        "cuad_dom_man_min",
        "cuad_dom_tar_min",
    ]
    return {key: int_or_zero(snapshot.get(key)) for key in keys}


def build_solicitud_data_remote(
    snapshot: dict[str, Any],
    persona_id: int,
    join_minutes: Callable[[Any, Any], int | None],
    int_or_zero: Callable[[Any], int],
    now_iso: str,
) -> dict[str, Any]:
    return {
        "persona_id": persona_id,
        "fecha_pedida": snapshot.get("fecha"),
        "desde_min": join_minutes(snapshot.get("desde_h"), snapshot.get("desde_m")),
        "hasta_min": join_minutes(snapshot.get("hasta_h"), snapshot.get("hasta_m")),
        "completo": 1 if int_or_zero(snapshot.get("completo")) else 0,
        "horas_solicitadas_min": int_or_zero(snapshot.get("minutos_total")),
        "notas": snapshot.get("notas") or "",
        "pdf_hash": snapshot.get("pdf_id") or "",
        "created_at": snapshot.get("created_at") or snapshot.get("fecha"),
        "updated_at": snapshot.get("updated_at") or now_iso,
        "source_device": snapshot.get("source_device"),
        "deleted": int_or_zero(snapshot.get("deleted")),
    }


def build_solicitud_data_local(snapshot: dict[str, Any], int_or_zero: Callable[[Any], int], now_iso: str) -> dict[str, Any]:
    return {
        "persona_id": int_or_zero(snapshot.get("persona_id")),
        "fecha_pedida": snapshot.get("fecha_pedida"),
        "desde_min": snapshot.get("desde_min"),
        "hasta_min": snapshot.get("hasta_min"),
        "completo": 1 if int_or_zero(snapshot.get("completo")) else 0,
        "horas_solicitadas_min": int_or_zero(snapshot.get("horas_solicitadas_min")),
        "notas": snapshot.get("notas") or "",
        "pdf_hash": snapshot.get("pdf_hash") or "",
        "created_at": snapshot.get("created_at") or snapshot.get("fecha_pedida"),
        "updated_at": snapshot.get("updated_at") or now_iso,
        "source_device": snapshot.get("source_device"),
        "deleted": int_or_zero(snapshot.get("deleted")),
    }


def solicitud_update_params(data: dict[str, Any], solicitud_id: int) -> tuple[Any, ...]:
    return (
        data["persona_id"],
        data["fecha_pedida"],
        data["desde_min"],
        data["hasta_min"],
        data["completo"],
        data["horas_solicitadas_min"],
        data["notas"],
        data["pdf_hash"],
        data["created_at"],
        data["updated_at"],
        data["source_device"],
        data["deleted"],
        solicitud_id,
    )


def solicitud_insert_params(uuid_value: str, data: dict[str, Any]) -> tuple[Any, ...]:
    return (
        uuid_value,
        data["persona_id"],
        data["created_at"],
        data["fecha_pedida"],
        data["desde_min"],
        data["hasta_min"],
        data["completo"],
        data["horas_solicitadas_min"],
        None,
        data["notas"],
        None,
        data["pdf_hash"],
        data["created_at"],
        data["updated_at"],
        data["source_device"],
        data["deleted"],
    )


def build_cuadrante_data_remote(
    snapshot: dict[str, Any],
    join_minutes: Callable[[Any, Any], int | None],
    int_or_zero: Callable[[Any], int],
    now_iso: str,
) -> dict[str, Any]:
    return {
        "delegada_uuid": snapshot.get("delegada_uuid"),
        "dia_semana": snapshot.get("dia_semana"),
        "man_min": join_minutes(snapshot.get("man_h"), snapshot.get("man_m")),
        "tar_min": join_minutes(snapshot.get("tar_h"), snapshot.get("tar_m")),
        "updated_at": snapshot.get("updated_at") or now_iso,
        "source_device": snapshot.get("source_device"),
        "deleted": int_or_zero(snapshot.get("deleted")),
    }


def build_cuadrante_data_local(snapshot: dict[str, Any], int_or_zero: Callable[[Any], int], now_iso: str) -> dict[str, Any]:
    return {
        "delegada_uuid": snapshot.get("delegada_uuid"),
        "dia_semana": snapshot.get("dia_semana"),
        "man_min": int_or_zero(snapshot.get("man_min")),
        "tar_min": int_or_zero(snapshot.get("tar_min")),
        "updated_at": snapshot.get("updated_at") or now_iso,
        "source_device": snapshot.get("source_device"),
        "deleted": int_or_zero(snapshot.get("deleted")),
    }
