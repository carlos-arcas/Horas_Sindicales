from __future__ import annotations

from datetime import date

import pytest

pytest.importorskip("PySide6.QtGui", exc_type=ImportError)

from app.ui.vistas.main_window_vista import MainWindow


class _DummySolicitud:
    def __init__(self, **values) -> None:
        for key, value in values.items():
            setattr(self, key, value)


def test_extraer_fecha_prioriza_fecha() -> None:
    item = _DummySolicitud(fecha=date(2025, 1, 3), fecha_solicitud=date(2025, 1, 2))

    resultado = MainWindow._extraer_fecha_solicitud(item)

    assert resultado == date(2025, 1, 3)


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
