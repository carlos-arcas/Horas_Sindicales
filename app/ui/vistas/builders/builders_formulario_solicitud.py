from __future__ import annotations

from typing import TYPE_CHECKING

from app.ui.vistas.builders.formulario_solicitud.builders_secciones import construir_layout_formulario

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


def create_formulario_solicitud(window: "MainWindow") -> None:
    construir_layout_formulario(window)
