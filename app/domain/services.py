from __future__ import annotations

from datetime import date, datetime
import logging

from app.core.errors import BusinessError, ValidationError

from app.domain.models import Persona, SheetsConfig, Solicitud


class ValidacionError(ValidationError):
    pass


class BusinessRuleError(BusinessError):
    pass


logger = logging.getLogger(__name__)


def validar_persona(persona: Persona) -> None:
    if not persona.nombre.strip():
        raise ValidacionError("El nombre es obligatorio.")
    if persona.genero not in {"M", "F"}:
        raise ValidacionError("El género debe ser 'M' o 'F'.")
    for campo, valor in {
        "horas_mes_min": persona.horas_mes_min,
        "horas_ano_min": persona.horas_ano_min,
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
    if solicitud.persona_id <= 0:
        raise ValidacionError("La solicitud debe tener delegada válida.")
    if solicitud.horas_solicitadas_min <= 0:
        raise ValidacionError("Las horas deben ser mayores a cero.")
    if not solicitud.fecha_solicitud or not solicitud.fecha_pedida:
        raise ValidacionError("Las fechas son obligatorias.")


def validar_sheets_config(config: SheetsConfig) -> None:
    if not config.spreadsheet_id.strip():
        raise ValidacionError("La URL o ID de la spreadsheet es obligatoria.")
    if not config.credentials_path.strip():
        raise ValidacionError("Debe seleccionar un archivo de credenciales JSON.")


def es_duplicada(solicitud_a: Solicitud, solicitud_b: Solicitud) -> bool:
    """Regla canónica de deduplicación de solicitudes.

    Dos solicitudes se consideran duplicadas solo si pertenecen a la misma
    delegada, al mismo día natural (YYYY-MM-DD) y sus tramos horarios solapan.
    """

    if solicitud_a.persona_id != solicitud_b.persona_id:
        return False

    fecha_a = _to_day(solicitud_a.fecha_pedida)
    fecha_b = _to_day(solicitud_b.fecha_pedida)
    if fecha_a != fecha_b:
        logger.debug(
            "Deduplicación sin conflicto por fecha: persona_id=%s fecha_a=%s fecha_b=%s inicio_a=%s fin_a=%s inicio_b=%s fin_b=%s",
            solicitud_a.persona_id,
            fecha_a.isoformat(),
            fecha_b.isoformat(),
            solicitud_a.desde_min,
            solicitud_a.hasta_min,
            solicitud_b.desde_min,
            solicitud_b.hasta_min,
        )
        return False

    solapa = _solapa_tramo(solicitud_a, solicitud_b)
    logger.debug(
        "Decisión deduplicación: persona_id=%s fecha_normalizada=%s inicio_a=%s fin_a=%s inicio_b=%s fin_b=%s solape=%s",
        solicitud_a.persona_id,
        fecha_a.isoformat(),
        solicitud_a.desde_min,
        solicitud_a.hasta_min,
        solicitud_b.desde_min,
        solicitud_b.hasta_min,
        solapa,
    )
    return solapa


def _to_day(value: str) -> date:
    raw = value.strip()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()


def _solapa_tramo(solicitud_a: Solicitud, solicitud_b: Solicitud) -> bool:
    if solicitud_a.completo or solicitud_b.completo:
        return True
    if (
        solicitud_a.desde_min is None
        or solicitud_a.hasta_min is None
        or solicitud_b.desde_min is None
        or solicitud_b.hasta_min is None
    ):
        return False
    return solicitud_a.desde_min < solicitud_b.hasta_min and solicitud_b.desde_min < solicitud_a.hasta_min
