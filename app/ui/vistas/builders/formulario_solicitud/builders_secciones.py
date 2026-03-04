from __future__ import annotations

from typing import TYPE_CHECKING

from app.ui.vistas.builders.formulario_solicitud.builders_pendientes import (
    adjuntar_tarjetas_y_tabs,
    construir_tarjeta_pendientes,
)
from app.ui.vistas.builders.formulario_solicitud.builders_solicitud import construir_tarjeta_solicitud

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


__all__ = [
    "adjuntar_tarjetas_y_tabs",
    "construir_tarjeta_pendientes",
    "construir_tarjeta_solicitud",
]


def construir_layout_formulario(window: "MainWindow") -> None:
    tarjeta_solicitud = construir_tarjeta_solicitud(window)
    tarjeta_pendientes = construir_tarjeta_pendientes(window)
    adjuntar_tarjetas_y_tabs(window, tarjeta_solicitud, tarjeta_pendientes)
