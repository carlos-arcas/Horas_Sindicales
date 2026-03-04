from __future__ import annotations

from typing import TYPE_CHECKING

from app.ui.vistas.builders.sync_panel.builders_secciones import (
    construir_tab_configuracion,
    construir_tab_sincronizacion,
)

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


def construir_panel_sync(window: "MainWindow") -> None:
    construir_tab_configuracion(window)
    construir_tab_sincronizacion(window)
    window.sync_diagnostics_button.toggled.connect(window.sync_diagnostics_content.setVisible)
