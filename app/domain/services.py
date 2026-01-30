from __future__ import annotations

from app.domain.models import Persona, Solicitud


class ValidacionError(ValueError):
    pass


class BusinessRuleError(ValueError):
    pass


def validar_persona(persona: Persona) -> None:
    if not persona.nombre.strip():
        raise ValidacionError("El nombre es obligatorio.")
    if persona.genero not in {"M", "F"}:
        raise ValidacionError("El género debe ser 'M' o 'F'.")
    for campo, valor in {
        "horas_mes_min": persona.horas_mes_min,
        "horas_ano_min": persona.horas_ano_min,
        "horas_jornada_defecto_min": persona.horas_jornada_defecto_min,
        "cuad_lun_man_min": persona.cuad_lun_man_min,
        "cuad_lun_tar_min": persona.cuad_lun_tar_min,
        "cuad_mar_man_min": persona.cuad_mar_man_min,
        "cuad_mar_tar_min": persona.cuad_mar_tar_min,
        "cuad_mie_man_min": persona.cuad_mie_man_min,
        "cuad_mie_tar_min": persona.cuad_mie_tar_min,
        "cuad_jue_man_min": persona.cuad_jue_man_min,
        "cuad_jue_tar_min": persona.cuad_jue_tar_min,
        "cuad_vie_man_min": persona.cuad_vie_man_min,
        "cuad_vie_tar_min": persona.cuad_vie_tar_min,
        "cuad_sab_man_min": persona.cuad_sab_man_min,
        "cuad_sab_tar_min": persona.cuad_sab_tar_min,
        "cuad_dom_man_min": persona.cuad_dom_man_min,
        "cuad_dom_tar_min": persona.cuad_dom_tar_min,
    }.items():
        if valor < 0:
            raise ValidacionError(f"{campo} no puede ser negativo.")


def validar_solicitud(solicitud: Solicitud) -> None:
    if solicitud.horas_solicitadas_min <= 0:
        raise ValidacionError("Las horas deben ser mayores a cero.")
    if not solicitud.fecha_solicitud or not solicitud.fecha_pedida:
        raise ValidacionError("Las fechas son obligatorias.")
