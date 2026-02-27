from __future__ import annotations

import pytest

from app.application.dto import SolicitudDTO

QDate = pytest.importorskip("PySide6.QtCore", exc_type=ImportError).QDate

try:
    from app.ui.historico_view import HistoricalViewModel
except ImportError as exc:  # pragma: no cover - depende de librerías Qt del entorno
    pytest.skip(f"PySide6 no disponible en entorno de test: {exc}", allow_module_level=True)


def _solicitud(
    solicitud_id: int,
    fecha_pedida: str,
    persona_id: int,
    notas: str,
    generated: bool,
) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=persona_id,
        fecha_solicitud=fecha_pedida,
        fecha_pedida=fecha_pedida,
        desde="09:00",
        hasta="11:00",
        completo=False,
        horas=2.0,
        observaciones="obs " + notas,
        pdf_path=None,
        pdf_hash=None,
        notas=notas,
        generated=generated,
    )


def _build_view_model() -> HistoricalViewModel:
    vm = HistoricalViewModel(
        [
            _solicitud(1, "2026-01-10", 1, "reunión centro norte", True),
            _solicitud(2, "2026-01-25", 2, "visita centro sur", False),
            _solicitud(3, "2026-02-11", 1, "asamblea general", True),
        ]
    )
    vm.set_persona_nombres({1: "Ana", 2: "Bea"})
    return vm


def test_filtra_por_texto() -> None:
    vm = _build_view_model()

    vm.proxy_model.set_search_text("asamblea")

    assert vm.proxy_model.rowCount() == 1


def test_filtra_por_rango_fechas() -> None:
    vm = _build_view_model()

    vm.proxy_model.set_date_range(QDate(2026, 1, 20), QDate(2026, 2, 1))

    assert vm.proxy_model.rowCount() == 1


def test_filtra_por_estado() -> None:
    vm = _build_view_model()

    vm.proxy_model.set_estado_code("PENDIENTE")

    assert vm.proxy_model.rowCount() == 1


def test_filtra_por_combinacion() -> None:
    vm = _build_view_model()

    vm.proxy_model.set_estado_code("CONFIRMADA")
    vm.proxy_model.set_delegada_id(1)
    vm.proxy_model.set_search_text("centro")
    vm.proxy_model.set_date_range(QDate(2026, 1, 1), QDate(2026, 1, 31))

    assert vm.proxy_model.rowCount() == 1


def test_sin_filtros_activos_devuelve_todas_las_filas() -> None:
    vm = _build_view_model()

    vm.proxy_model.set_filters(
        delegada_id=None,
        ver_todas=True,
        year_mode="RANGE",
        year=None,
        month=None,
        date_from=None,
        date_to=None,
    )

    assert vm.proxy_model.rowCount() == vm.source_model.rowCount()


def test_ver_todas_true_ignora_filtro_de_delegada() -> None:
    vm = _build_view_model()

    vm.proxy_model.set_filters(
        delegada_id=999,
        ver_todas=True,
        year_mode="RANGE",
        year=None,
        month=None,
        date_from=None,
        date_to=None,
    )

    assert vm.proxy_model.rowCount() == vm.source_model.rowCount()


def test_rango_excluye_fecha_fuera_de_limite_con_tipo_date() -> None:
    vm = _build_view_model()
    vm.source_model._fecha_pedida_dates[0] = "02/03/2026"

    vm.proxy_model.set_date_range(QDate(2026, 1, 28), QDate(2026, 2, 27))

    assert vm.proxy_model.rowCount() == 1


def test_rango_muestra_fecha_dentro_de_limite() -> None:
    vm = _build_view_model()

    vm.proxy_model.set_date_range(QDate(2026, 2, 1), QDate(2026, 2, 28))

    assert vm.proxy_model.rowCount() == 1
