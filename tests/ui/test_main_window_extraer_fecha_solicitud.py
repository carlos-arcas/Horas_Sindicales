from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

pytest.importorskip("PySide6.QtGui", exc_type=ImportError)

from app.application.dto import SolicitudDTO
from app.ui.vistas.main_window_vista import MainWindow


class _DummySolicitud:
    def __init__(self, **values) -> None:
        for key, value in values.items():
            setattr(self, key, value)


def test_extraer_fecha_prioriza_fecha_solicitud_canonicamente() -> None:
    item = _DummySolicitud(fecha=date(2025, 1, 3), fecha_solicitud=date(2025, 1, 2))

    resultado = MainWindow._extraer_fecha_solicitud(item)

    assert resultado == date(2025, 1, 2)


def test_extraer_fecha_usa_campos_alternativos_y_parsea_iso() -> None:
    item = _DummySolicitud(fecha_inicio="2025-02-11")

    resultado = MainWindow._extraer_fecha_solicitud(item)

    assert resultado == date(2025, 2, 11)


def test_extraer_fecha_devuelve_none_en_formato_no_iso() -> None:
    item = _DummySolicitud(fecha_desde="11/02/2025")

    resultado = MainWindow._extraer_fecha_solicitud(item)

    assert resultado is None


def test_extraer_fecha_devuelve_none_si_no_hay_campos() -> None:
    item = _DummySolicitud(otra_cosa="valor")

    resultado = MainWindow._extraer_fecha_solicitud(item)

    assert resultado is None


def test_refresh_resumen_kpis_admite_solicitudes_dto_reales_sin_excepcion() -> None:
    solicitud = SolicitudDTO(
        id=1,
        persona_id=7,
        fecha_solicitud=date.today().isoformat(),
        fecha_pedida="2025-01-15",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
    )
    page_resumen = SimpleNamespace(
        kpi_solicitudes_hoy=SimpleNamespace(value_label=SimpleNamespace(setText=Mock())),
        kpi_pendientes=SimpleNamespace(value_label=SimpleNamespace(setText=Mock())),
        kpi_ultima_sync=SimpleNamespace(value_label=SimpleNamespace(setText=Mock())),
        kpi_saldo_restante=SimpleNamespace(value_label=SimpleNamespace(setText=Mock())),
        set_recientes=Mock(),
    )
    window = SimpleNamespace(
        page_resumen=page_resumen,
        _pending_solicitudes=[solicitud],
        _sync_service=SimpleNamespace(get_last_sync_at=Mock(return_value=None)),
        _current_persona=Mock(return_value=None),
        _update_global_context=Mock(),
        _extraer_fecha_solicitud=MainWindow._extraer_fecha_solicitud,
    )

    MainWindow._refresh_resumen_kpis(window)

    page_resumen.kpi_solicitudes_hoy.value_label.setText.assert_called_once_with("1")
    page_resumen.kpi_pendientes.value_label.setText.assert_called_once_with("1")
