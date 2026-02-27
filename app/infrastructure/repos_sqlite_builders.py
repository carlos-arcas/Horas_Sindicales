from __future__ import annotations

from typing import Iterable

from app.domain.models import Persona, Solicitud


# Columnas compartidas para evitar divergencias entre queries de Persona.
PERSONA_SELECT_FIELDS = """
    id, nombre, genero,
    horas_mes_min, horas_ano_min, horas_jornada_defecto_min,
    is_active,
    cuad_lun_man_min, cuad_lun_tar_min,
    cuad_mar_man_min, cuad_mar_tar_min,
    cuad_mie_man_min, cuad_mie_tar_min,
    cuad_jue_man_min, cuad_jue_tar_min,
    cuad_vie_man_min, cuad_vie_tar_min,
    cuad_sab_man_min, cuad_sab_tar_min,
    cuad_dom_man_min, cuad_dom_tar_min,
    cuadrante_uniforme, trabaja_finde
""".strip()

SOLICITUD_SELECT_FIELDS = """
    id, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
    horas_solicitadas_min, observaciones, notas, pdf_path, pdf_hash, generated
""".strip()


def int_or_zero(value: int | None) -> int:
    return 0 if value is None else int(value)


def bool_from_db(value: int | None) -> bool | None:
    if value is None:
        return None
    return bool(value)


def row_to_persona(row: dict[str, object]) -> Persona:
    claves = set(row.keys())
    return Persona(
        id=row["id"],
        nombre=row["nombre"],
        genero=row["genero"],
        horas_mes_min=int_or_zero(row["horas_mes_min"]),
        horas_ano_min=int_or_zero(row["horas_ano_min"]),
        is_active=bool_from_db(row["is_active"]) if "is_active" in claves else True,
        cuad_lun_man_min=int_or_zero(row["cuad_lun_man_min"]),
        cuad_lun_tar_min=int_or_zero(row["cuad_lun_tar_min"]),
        cuad_mar_man_min=int_or_zero(row["cuad_mar_man_min"]),
        cuad_mar_tar_min=int_or_zero(row["cuad_mar_tar_min"]),
        cuad_mie_man_min=int_or_zero(row["cuad_mie_man_min"]),
        cuad_mie_tar_min=int_or_zero(row["cuad_mie_tar_min"]),
        cuad_jue_man_min=int_or_zero(row["cuad_jue_man_min"]),
        cuad_jue_tar_min=int_or_zero(row["cuad_jue_tar_min"]),
        cuad_vie_man_min=int_or_zero(row["cuad_vie_man_min"]),
        cuad_vie_tar_min=int_or_zero(row["cuad_vie_tar_min"]),
        cuad_sab_man_min=int_or_zero(row["cuad_sab_man_min"]),
        cuad_sab_tar_min=int_or_zero(row["cuad_sab_tar_min"]),
        cuad_dom_man_min=int_or_zero(row["cuad_dom_man_min"]),
        cuad_dom_tar_min=int_or_zero(row["cuad_dom_tar_min"]),
        cuadrante_uniforme=bool_from_db(row["cuadrante_uniforme"]) if "cuadrante_uniforme" in claves else False,
        trabaja_finde=bool_from_db(row["trabaja_finde"]) if "trabaja_finde" in claves else False,
    )


def persona_insert_params(persona: Persona, persona_uuid: str, updated_at: str) -> tuple[object, ...]:
    return (
        persona_uuid,
        persona.nombre,
        persona.genero,
        persona.horas_mes_min,
        persona.horas_ano_min,
        0,
        1 if persona.is_active else 0,
        persona.cuad_lun_man_min,
        persona.cuad_lun_tar_min,
        persona.cuad_mar_man_min,
        persona.cuad_mar_tar_min,
        persona.cuad_mie_man_min,
        persona.cuad_mie_tar_min,
        persona.cuad_jue_man_min,
        persona.cuad_jue_tar_min,
        persona.cuad_vie_man_min,
        persona.cuad_vie_tar_min,
        persona.cuad_sab_man_min,
        persona.cuad_sab_tar_min,
        persona.cuad_dom_man_min,
        persona.cuad_dom_tar_min,
        1 if persona.cuadrante_uniforme else 0,
        1 if persona.trabaja_finde else 0,
        updated_at,
        0,
    )


def persona_update_params(persona: Persona, updated_at: str) -> tuple[object, ...]:
    return (
        persona.nombre,
        persona.genero,
        persona.horas_mes_min,
        persona.horas_ano_min,
        0,
        1 if persona.is_active else 0,
        persona.cuad_lun_man_min,
        persona.cuad_lun_tar_min,
        persona.cuad_mar_man_min,
        persona.cuad_mar_tar_min,
        persona.cuad_mie_man_min,
        persona.cuad_mie_tar_min,
        persona.cuad_jue_man_min,
        persona.cuad_jue_tar_min,
        persona.cuad_vie_man_min,
        persona.cuad_vie_tar_min,
        persona.cuad_sab_man_min,
        persona.cuad_sab_tar_min,
        persona.cuad_dom_man_min,
        persona.cuad_dom_tar_min,
        1 if persona.cuadrante_uniforme else 0,
        1 if persona.trabaja_finde else 0,
        updated_at,
        persona.id,
    )


def solicitud_insert_params(solicitud: Solicitud, solicitud_uuid: str, created_at: str) -> tuple[object, ...]:
    return (
        solicitud_uuid,
        solicitud.persona_id,
        solicitud.fecha_solicitud,
        solicitud.fecha_pedida,
        solicitud.desde_min,
        solicitud.hasta_min,
        int(solicitud.completo),
        solicitud.horas_solicitadas_min,
        solicitud.observaciones,
        solicitud.notas or "",
        solicitud.pdf_path,
        solicitud.pdf_hash,
        0,
        created_at,
        created_at,
        0,
    )


def build_solicitud_candidate(
    persona_id: int,
    fecha_pedida: str,
    desde_min: int | None,
    hasta_min: int | None,
    completo: bool,
) -> Solicitud:
    return Solicitud(
        id=None,
        persona_id=persona_id,
        fecha_solicitud=fecha_pedida,
        fecha_pedida=fecha_pedida,
        desde_min=desde_min,
        hasta_min=hasta_min,
        completo=completo,
        horas_solicitadas_min=0,
        observaciones=None,
        notas=None,
        pdf_path=None,
        pdf_hash=None,
        generated=False,
    )


def build_period_filters(year: int, month: int | None = None) -> tuple[str, tuple[str, ...]]:
    if month is None:
        return "strftime('%Y', fecha_pedida) = ?", (f"{year:04d}",)
    return "strftime('%Y', fecha_pedida) = ? AND strftime('%m', fecha_pedida) = ?", (f"{year:04d}", f"{month:02d}")


def build_soft_delete_many_sql(ids: Iterable[int]) -> tuple[str, list[object]]:
    ids_list = list(ids)
    placeholders = ",".join("?" for _ in ids_list)
    return f"UPDATE solicitudes SET deleted = 1, updated_at = ? WHERE id IN ({placeholders})", ids_list
