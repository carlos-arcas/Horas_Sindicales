from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.services import (
    DecisionFiltroAplicacion,
    EntradaFiltroHistorico,
    RegistroHistoricoAplicacion,
    coincide_anio,
    coincide_anio_mes,
    coincide_busqueda,
    coincide_delegada,
    coincide_estado,
    coincide_modo_fecha,
    coincide_rango_fechas,
    decidir_aceptacion,
    hay_filtro_periodo,
    hay_filtros,
    normalizar_texto,
)


@dataclass(frozen=True)
class FiltroHistoricoEntrada:
    search_pattern: str
    year_mode: str | None
    year: int | None
    month: int | None
    date_from: date | None
    date_to: date | None
    estado_code: str | None
    delegada_id: int | None
    ver_todas: bool


@dataclass(frozen=True)
class RegistroHistorico:
    persona_id: int | None
    fecha: date | None
    estado_code: str
    haystack: str


@dataclass(frozen=True)
class DecisionFiltro:
    accept: bool
    reason_code: str


def _a_entrada_aplicacion(entrada: FiltroHistoricoEntrada) -> EntradaFiltroHistorico:
    return EntradaFiltroHistorico(
        patron_busqueda=entrada.search_pattern,
        modo_anio=entrada.year_mode,
        anio=entrada.year,
        mes=entrada.month,
        fecha_desde=entrada.date_from,
        fecha_hasta=entrada.date_to,
        codigo_estado=entrada.estado_code,
        id_delegada=entrada.delegada_id,
        ver_todas=entrada.ver_todas,
    )


def _a_registro_aplicacion(registro: RegistroHistorico) -> RegistroHistoricoAplicacion:
    return RegistroHistoricoAplicacion(
        id_persona=registro.persona_id,
        fecha=registro.fecha,
        codigo_estado=registro.estado_code,
        texto_busqueda=registro.haystack,
    )


def _a_decision_compat(decision: DecisionFiltroAplicacion) -> DecisionFiltro:
    return DecisionFiltro(accept=decision.acepta, reason_code=decision.codigo_razon)


def has_filters(entrada: FiltroHistoricoEntrada) -> bool:
    return hay_filtros(_a_entrada_aplicacion(entrada))


def has_period_filter(entrada: FiltroHistoricoEntrada) -> bool:
    return hay_filtro_periodo(_a_entrada_aplicacion(entrada))


def matches_delegada(entrada: FiltroHistoricoEntrada, row: RegistroHistorico) -> bool:
    return coincide_delegada(_a_entrada_aplicacion(entrada), _a_registro_aplicacion(row))


def matches_date_mode(entrada: FiltroHistoricoEntrada, row: RegistroHistorico) -> bool:
    return coincide_modo_fecha(_a_entrada_aplicacion(entrada), _a_registro_aplicacion(row))


matches_year = coincide_anio
matches_year_month = coincide_anio_mes
matches_rango_fechas = coincide_rango_fechas


def matches_estado(estado_code: str | None, row: RegistroHistorico) -> bool:
    return coincide_estado(estado_code, _a_registro_aplicacion(row))


def matches_busqueda(search_pattern: str, haystack: str) -> bool:
    return coincide_busqueda(search_pattern, haystack)


def decide_accept(entrada: FiltroHistoricoEntrada, row: RegistroHistorico) -> DecisionFiltro:
    decision = decidir_aceptacion(_a_entrada_aplicacion(entrada), _a_registro_aplicacion(row))
    return _a_decision_compat(decision)


__all__ = [
    "DecisionFiltro",
    "FiltroHistoricoEntrada",
    "RegistroHistorico",
    "decide_accept",
    "has_filters",
    "has_period_filter",
    "matches_busqueda",
    "matches_date_mode",
    "matches_delegada",
    "matches_estado",
    "matches_rango_fechas",
    "matches_year",
    "matches_year_month",
    "normalizar_texto",
]
