from __future__ import annotations

from datetime import date, datetime
import logging

from app.core.errors import BusinessError, ValidationError

from app.domain.models import Persona, SheetsConfig, Solicitud
from app.domain.time_range import normalize_range, overlaps


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
    try:
        inicio_a, fin_a = normalize_range(
            completo=solicitud_a.completo,
            desde_min=solicitud_a.desde_min,
            hasta_min=solicitud_a.hasta_min,
        )
        inicio_b, fin_b = normalize_range(
            completo=solicitud_b.completo,
            desde_min=solicitud_b.desde_min,
            hasta_min=solicitud_b.hasta_min,
        )
    except ValidationError:
        return False
    return overlaps(inicio_a, fin_a, inicio_b, fin_b)


from dataclasses import dataclass
import re


@dataclass(frozen=True)
class EntradaFiltroHistorico:
    patron_busqueda: str
    modo_anio: str | None
    anio: int | None
    mes: int | None
    fecha_desde: date | None
    fecha_hasta: date | None
    codigo_estado: str | None
    id_delegada: int | None
    ver_todas: bool


@dataclass(frozen=True)
class RegistroHistoricoAplicacion:
    id_persona: int | None
    fecha: date | None
    codigo_estado: str
    texto_busqueda: str


@dataclass(frozen=True)
class DecisionFiltroAplicacion:
    acepta: bool
    codigo_razon: str


def normalizar_texto(value: str) -> str:
    return value.strip()


def hay_filtros(entrada: EntradaFiltroHistorico) -> bool:
    hay_filtro_delegada = not entrada.ver_todas and entrada.id_delegada is not None
    return any(
        (
            hay_filtro_delegada,
            hay_filtro_periodo(entrada),
            bool(entrada.codigo_estado),
            bool(normalizar_texto(entrada.patron_busqueda)),
        )
    )


def hay_filtro_periodo(entrada: EntradaFiltroHistorico) -> bool:
    if entrada.modo_anio == "ALL_YEAR":
        return entrada.anio is not None
    if entrada.modo_anio == "YEAR_MONTH":
        return entrada.anio is not None and entrada.mes is not None
    if entrada.modo_anio == "RANGE":
        return entrada.fecha_desde is not None or entrada.fecha_hasta is not None
    return False


def coincide_delegada(entrada: EntradaFiltroHistorico, fila: RegistroHistoricoAplicacion) -> bool:
    if entrada.ver_todas or entrada.id_delegada is None:
        return True
    return fila.id_persona == entrada.id_delegada


def coincide_modo_fecha(entrada: EntradaFiltroHistorico, fila: RegistroHistoricoAplicacion) -> bool:
    if entrada.modo_anio == "ALL_YEAR":
        return coincide_anio(entrada.anio, fila.fecha)
    if entrada.modo_anio == "YEAR_MONTH":
        return coincide_anio_mes(entrada.anio, entrada.mes, fila.fecha)
    if entrada.modo_anio == "RANGE":
        return coincide_rango_fechas(entrada.fecha_desde, entrada.fecha_hasta, fila.fecha)
    return True


def coincide_anio(anio: int | None, fecha: date | None) -> bool:
    if anio is None:
        return True
    if fecha is None:
        return False
    return fecha.year == anio


def coincide_anio_mes(anio: int | None, mes: int | None, fecha: date | None) -> bool:
    if anio is None or mes is None:
        return True
    if fecha is None:
        return False
    return fecha.year == anio and fecha.month == mes


def coincide_rango_fechas(fecha_desde: date | None, fecha_hasta: date | None, fecha: date | None) -> bool:
    if not fecha_desde and not fecha_hasta:
        return True
    if fecha is None:
        return True
    if fecha_desde and fecha < fecha_desde:
        return False
    if fecha_hasta and fecha > fecha_hasta:
        return False
    return True


def coincide_estado(codigo_estado: str | None, fila: RegistroHistoricoAplicacion) -> bool:
    if not codigo_estado:
        return True
    return fila.codigo_estado == codigo_estado


def coincide_busqueda(patron_busqueda: str, texto_busqueda: str) -> bool:
    patron = normalizar_texto(patron_busqueda)
    if not patron:
        return True
    return re.search(patron, texto_busqueda, flags=re.IGNORECASE) is not None


def decidir_aceptacion(entrada: EntradaFiltroHistorico, fila: RegistroHistoricoAplicacion) -> DecisionFiltroAplicacion:
    if not hay_filtros(entrada):
        return DecisionFiltroAplicacion(acepta=True, codigo_razon="no_filters")

    if not coincide_delegada(entrada, fila):
        return DecisionFiltroAplicacion(acepta=False, codigo_razon="delegada_mismatch")

    if not coincide_modo_fecha(entrada, fila):
        return DecisionFiltroAplicacion(acepta=False, codigo_razon="date_mismatch")

    if not coincide_estado(entrada.codigo_estado, fila):
        return DecisionFiltroAplicacion(acepta=False, codigo_razon="estado_mismatch")

    if not coincide_busqueda(entrada.patron_busqueda, fila.texto_busqueda):
        return DecisionFiltroAplicacion(acepta=False, codigo_razon="search_mismatch")

    return DecisionFiltroAplicacion(acepta=True, codigo_razon="accepted")
