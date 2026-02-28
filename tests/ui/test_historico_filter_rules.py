from __future__ import annotations

from datetime import date

import pytest

from app.ui.vistas.historico_filter_rules import (
    DecisionFiltro,
    FiltroHistoricoEntrada,
    RegistroHistorico,
    decide_accept,
)

pytestmark = pytest.mark.headless_safe


def _entrada(
    *,
    search_pattern: str = "",
    year_mode: str | None = None,
    year: int | None = None,
    month: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    estado_code: str | None = None,
    delegada_id: int | None = None,
    ver_todas: bool = True,
) -> FiltroHistoricoEntrada:
    return FiltroHistoricoEntrada(
        search_pattern=search_pattern,
        year_mode=year_mode,
        year=year,
        month=month,
        date_from=date_from,
        date_to=date_to,
        estado_code=estado_code,
        delegada_id=delegada_id,
        ver_todas=ver_todas,
    )


def _row(
    *,
    persona_id: int | None = 1,
    fecha: date | None = date(2026, 2, 15),
    estado_code: str = "PENDIENTE",
    haystack: str = "Ana pendiente 2026-02-15",
) -> RegistroHistorico:
    return RegistroHistorico(persona_id=persona_id, fecha=fecha, estado_code=estado_code, haystack=haystack)


@pytest.mark.parametrize(
    ("entrada", "row", "accepted"),
    [
        (_entrada(), _row(), True),
        (_entrada(), _row(persona_id=2), True),
        (_entrada(), _row(fecha=None), True),
    ],
)
def test_sin_filtros_acepta_todo(entrada: FiltroHistoricoEntrada, row: RegistroHistorico, accepted: bool) -> None:
    assert decide_accept(entrada, row).accept is accepted


@pytest.mark.parametrize(
    ("search_pattern", "haystack", "accepted"),
    [
        ("ana", "Ana pendiente", True),
        ("PENDIENTE", "ana pendiente", True),
        ("Ana.*pend", "Ana pendiente", True),
        ("confirmada", "Ana pendiente", False),
        ("", "texto cualquiera", True),
    ],
)
def test_busqueda_case_insensitive_y_substring(search_pattern: str, haystack: str, accepted: bool) -> None:
    entrada = _entrada(search_pattern=search_pattern)
    row = _row(haystack=haystack)
    assert decide_accept(entrada, row).accept is accepted


@pytest.mark.parametrize(
    ("date_from", "date_to", "fecha", "accepted"),
    [
        (None, None, date(2026, 1, 1), True),
        (date(2026, 2, 1), None, date(2026, 1, 31), False),
        (date(2026, 2, 1), None, date(2026, 2, 1), True),
        (None, date(2026, 2, 28), date(2026, 3, 1), False),
        (None, date(2026, 2, 28), date(2026, 2, 28), True),
        (date(2026, 2, 1), date(2026, 2, 28), date(2026, 2, 15), True),
        (date(2026, 2, 1), date(2026, 2, 28), None, True),
    ],
)
def test_rango_fechas(date_from: date | None, date_to: date | None, fecha: date | None, accepted: bool) -> None:
    entrada = _entrada(year_mode="RANGE", date_from=date_from, date_to=date_to)
    row = _row(fecha=fecha)
    assert decide_accept(entrada, row).accept is accepted


@pytest.mark.parametrize(
    ("year_mode", "year", "month", "fecha", "accepted"),
    [
        ("ALL_YEAR", 2026, None, date(2026, 1, 1), True),
        ("ALL_YEAR", 2026, None, date(2025, 12, 31), False),
        ("ALL_YEAR", 2026, None, None, False),
        ("YEAR_MONTH", 2026, 2, date(2026, 2, 10), True),
        ("YEAR_MONTH", 2026, 2, date(2026, 3, 10), False),
        ("YEAR_MONTH", 2026, 2, None, False),
        ("YEAR_MONTH", 2026, None, date(2026, 2, 10), True),
    ],
)
def test_modo_year_y_year_month(
    year_mode: str,
    year: int | None,
    month: int | None,
    fecha: date | None,
    accepted: bool,
) -> None:
    entrada = _entrada(year_mode=year_mode, year=year, month=month)
    row = _row(fecha=fecha)
    assert decide_accept(entrada, row).accept is accepted


@pytest.mark.parametrize(
    ("estado_code", "row_estado", "accepted"),
    [
        (None, "PENDIENTE", True),
        ("PENDIENTE", "PENDIENTE", True),
        ("CONFIRMADA", "PENDIENTE", False),
        ("CONFIRMADA", "CONFIRMADA", True),
    ],
)
def test_estado_filter(estado_code: str | None, row_estado: str, accepted: bool) -> None:
    entrada = _entrada(estado_code=estado_code)
    row = _row(estado_code=row_estado)
    assert decide_accept(entrada, row).accept is accepted


@pytest.mark.parametrize(
    ("delegada_id", "ver_todas", "persona_id", "accepted"),
    [
        (None, True, 1, True),
        (2, True, 1, True),
        (2, False, 2, True),
        (2, False, 1, False),
    ],
)
def test_delegada_filter(delegada_id: int | None, ver_todas: bool, persona_id: int, accepted: bool) -> None:
    entrada = _entrada(delegada_id=delegada_id, ver_todas=ver_todas)
    row = _row(persona_id=persona_id)
    assert decide_accept(entrada, row).accept is accepted


@pytest.mark.parametrize(
    ("entrada", "row", "expected"),
    [
        (
            _entrada(delegada_id=2, ver_todas=False, search_pattern="ana", estado_code="PENDIENTE"),
            _row(persona_id=1, estado_code="PENDIENTE", haystack="ana"),
            DecisionFiltro(False, "delegada_mismatch"),
        ),
        (
            _entrada(
                delegada_id=1,
                ver_todas=False,
                year_mode="ALL_YEAR",
                year=2026,
                estado_code="PENDIENTE",
                search_pattern="ana",
            ),
            _row(persona_id=1, fecha=date(2025, 1, 1), estado_code="PENDIENTE", haystack="ana"),
            DecisionFiltro(False, "date_mismatch"),
        ),
        (
            _entrada(
                delegada_id=1,
                ver_todas=False,
                year_mode="ALL_YEAR",
                year=2026,
                estado_code="CONFIRMADA",
                search_pattern="ana",
            ),
            _row(persona_id=1, fecha=date(2026, 1, 1), estado_code="PENDIENTE", haystack="ana"),
            DecisionFiltro(False, "estado_mismatch"),
        ),
        (
            _entrada(
                delegada_id=1,
                ver_todas=False,
                year_mode="ALL_YEAR",
                year=2026,
                estado_code="PENDIENTE",
                search_pattern="confirmada",
            ),
            _row(persona_id=1, fecha=date(2026, 1, 1), estado_code="PENDIENTE", haystack="ana"),
            DecisionFiltro(False, "search_mismatch"),
        ),
        (
            _entrada(
                delegada_id=1,
                ver_todas=False,
                year_mode="ALL_YEAR",
                year=2026,
                estado_code="PENDIENTE",
                search_pattern="ana",
            ),
            _row(persona_id=1, fecha=date(2026, 1, 1), estado_code="PENDIENTE", haystack="Ana"),
            DecisionFiltro(True, "accepted"),
        ),
        (
            _entrada(),
            _row(),
            DecisionFiltro(True, "no_filters"),
        ),
    ],
)
def test_reason_code_contrato_precedencia(
    entrada: FiltroHistoricoEntrada,
    row: RegistroHistorico,
    expected: DecisionFiltro,
) -> None:
    assert decide_accept(entrada, row) == expected
