from __future__ import annotations

from dataclasses import dataclass

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.normalizacion_solicitud import (
    SolicitudNormalizada,
    normalizar_solicitud,
)
from app.domain.time_range import TimeRangeValidationError, overlaps
from app.domain.time_utils import parse_hhmm


@dataclass(frozen=True)
class ResultadoDuplicado:
    hay_duplicado: bool
    clave: tuple[int, str, str, str, str] | None


def detectar_duplicado(
    solicitud: SolicitudDTO,
    existentes: list[SolicitudDTO],
    *,
    excluir_por_id: str | int | None = None,
    excluir_por_indice: int | None = None,
) -> ResultadoDuplicado:
    try:
        objetivo = normalizar_solicitud(solicitud)
    except (TimeRangeValidationError, ValueError):
        return ResultadoDuplicado(hay_duplicado=False, clave=None)

    for idx, existente in enumerate(existentes):
        if _debe_excluir(existente, idx, excluir_por_id, excluir_por_indice):
            continue
        if _esta_eliminado(existente):
            continue
        try:
            normalizada = normalizar_solicitud(existente)
        except (TimeRangeValidationError, ValueError):
            continue
        if _es_duplicado(objetivo, normalizada):
            clave = _clave_desde_normalizada(normalizada)
            return ResultadoDuplicado(hay_duplicado=True, clave=clave)

    return ResultadoDuplicado(hay_duplicado=False, clave=None)


def detectar_duplicados_en_pendientes(
    pendientes: list[SolicitudDTO],
) -> set[tuple[int, str, str, str, str]]:
    conteo: dict[tuple[int, str, str, str, str], int] = {}
    for pendiente in pendientes:
        if _esta_eliminado(pendiente):
            continue
        try:
            normalizada = normalizar_solicitud(pendiente)
        except (TimeRangeValidationError, ValueError):
            continue
        clave = _clave_desde_normalizada(normalizada)
        conteo[clave] = conteo.get(clave, 0) + 1
    return {clave for clave, repeticiones in conteo.items() if repeticiones >= 2}


def _es_duplicado(a: SolicitudNormalizada, b: SolicitudNormalizada) -> bool:
    if a.persona_id != b.persona_id or a.fecha != b.fecha:
        return False
    a_inicio, a_fin = _rango_para_solape(a)
    b_inicio, b_fin = _rango_para_solape(b)
    return overlaps(a_inicio, a_fin, b_inicio, b_fin)


def _rango_para_solape(solicitud: SolicitudNormalizada) -> tuple[int, int]:
    if solicitud.completo:
        return 0, 24 * 60
    return parse_hhmm(solicitud.desde), parse_hhmm(solicitud.hasta)


def _debe_excluir(
    existente: SolicitudDTO,
    indice: int,
    excluir_por_id: str | int | None,
    excluir_por_indice: int | None,
) -> bool:
    if excluir_por_id is not None and existente.id is not None and str(existente.id) == str(excluir_por_id):
        return True
    return existente.id is None and excluir_por_indice is not None and indice == excluir_por_indice


def _esta_eliminado(dto: SolicitudDTO) -> bool:
    return bool(getattr(dto, "deleted", 0))


def _clave_desde_normalizada(solicitud: SolicitudNormalizada) -> tuple[int, str, str, str, str]:
    return (solicitud.persona_id, solicitud.fecha, solicitud.desde, solicitud.hasta, solicitud.tipo)
