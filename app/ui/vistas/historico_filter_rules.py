from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re


@dataclass(frozen=True)
class FiltroHistoricoEntrada:
    """Parámetros de filtrado del histórico.

    Precedencia (orden de descarte) pensada para debugging estable y sencilla para juniors:
    1) Si no hay filtros activos -> acepta todo.
    2) Filtro por delegada -> descarta pronto por ser comparación O(1).
    3) Filtro temporal (año/mes/rango) -> reduce universo antes del texto.
    4) Filtro de estado -> valida la semántica de negocio.
    5) Búsqueda textual -> último paso porque suele ser el más costoso.
    """

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


def normalizar_texto(value: str) -> str:
    return value.strip()


def has_filters(entrada: FiltroHistoricoEntrada) -> bool:
    has_delegada_filter = not entrada.ver_todas and entrada.delegada_id is not None
    return any((
        has_delegada_filter,
        has_period_filter(entrada),
        bool(entrada.estado_code),
        bool(normalizar_texto(entrada.search_pattern)),
    ))


def has_period_filter(entrada: FiltroHistoricoEntrada) -> bool:
    if entrada.year_mode == "ALL_YEAR":
        return entrada.year is not None
    if entrada.year_mode == "YEAR_MONTH":
        return entrada.year is not None and entrada.month is not None
    if entrada.year_mode == "RANGE":
        return entrada.date_from is not None or entrada.date_to is not None
    return False


def matches_delegada(entrada: FiltroHistoricoEntrada, row: RegistroHistorico) -> bool:
    if entrada.ver_todas or entrada.delegada_id is None:
        return True
    return row.persona_id == entrada.delegada_id


def matches_date_mode(entrada: FiltroHistoricoEntrada, row: RegistroHistorico) -> bool:
    if entrada.year_mode == "ALL_YEAR":
        return matches_year(entrada.year, row.fecha)
    if entrada.year_mode == "YEAR_MONTH":
        return matches_year_month(entrada.year, entrada.month, row.fecha)
    if entrada.year_mode == "RANGE":
        return matches_rango_fechas(entrada.date_from, entrada.date_to, row.fecha)
    return True


def matches_year(year: int | None, fecha: date | None) -> bool:
    if year is None:
        return True
    if fecha is None:
        return False
    return fecha.year == year


def matches_year_month(year: int | None, month: int | None, fecha: date | None) -> bool:
    if year is None or month is None:
        return True
    if fecha is None:
        return False
    return fecha.year == year and fecha.month == month


def matches_rango_fechas(date_from: date | None, date_to: date | None, fecha: date | None) -> bool:
    if not date_from and not date_to:
        return True
    if fecha is None:
        return True
    if date_from and fecha < date_from:
        return False
    if date_to and fecha > date_to:
        return False
    return True


def matches_estado(estado_code: str | None, row: RegistroHistorico) -> bool:
    if not estado_code:
        return True
    return row.estado_code == estado_code


def matches_busqueda(search_pattern: str, haystack: str) -> bool:
    pattern = normalizar_texto(search_pattern)
    if not pattern:
        return True
    return re.search(pattern, haystack, flags=re.IGNORECASE) is not None


def decide_accept(entrada: FiltroHistoricoEntrada, row: RegistroHistorico) -> DecisionFiltro:
    if not has_filters(entrada):
        return DecisionFiltro(accept=True, reason_code="no_filters")

    if not matches_delegada(entrada, row):
        return DecisionFiltro(accept=False, reason_code="delegada_mismatch")

    if not matches_date_mode(entrada, row):
        return DecisionFiltro(accept=False, reason_code="date_mismatch")

    if not matches_estado(entrada.estado_code, row):
        return DecisionFiltro(accept=False, reason_code="estado_mismatch")

    if not matches_busqueda(entrada.search_pattern, row.haystack):
        return DecisionFiltro(accept=False, reason_code="search_mismatch")

    return DecisionFiltro(accept=True, reason_code="accepted")
