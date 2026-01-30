from __future__ import annotations

from app.domain.models import Persona, Solicitud


class ValidacionError(ValueError):
    pass


def validar_persona(persona: Persona) -> None:
    if not persona.nombre.strip():
        raise ValidacionError("El nombre es obligatorio.")
    if persona.genero not in {"M", "F"}:
        raise ValidacionError("El género debe ser 'M' o 'F'.")
    for campo, valor in {
        "horas_mes": persona.horas_mes,
        "horas_ano": persona.horas_ano,
        "horas_jornada_defecto": persona.horas_jornada_defecto,
        "cuad_lun": persona.cuad_lun,
        "cuad_mar": persona.cuad_mar,
        "cuad_mie": persona.cuad_mie,
        "cuad_jue": persona.cuad_jue,
        "cuad_vie": persona.cuad_vie,
        "cuad_sab": persona.cuad_sab,
        "cuad_dom": persona.cuad_dom,
    }.items():
        if valor < 0:
            raise ValidacionError(f"{campo} no puede ser negativo.")


def validar_solicitud(solicitud: Solicitud) -> None:
    if solicitud.horas < 0:
        raise ValidacionError("Las horas no pueden ser negativas.")
    if not solicitud.fecha_solicitud or not solicitud.fecha_pedida:
        raise ValidacionError("Las fechas son obligatorias.")
