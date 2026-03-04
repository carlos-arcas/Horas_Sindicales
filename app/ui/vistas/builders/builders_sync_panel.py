from __future__ import annotations

from typing import TYPE_CHECKING

from app.ui.vistas.builders.sync_panel.orquestacion_sync_panel import construir_panel_sync

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


def create_sync_panel(window: "MainWindow") -> None:
    construir_panel_sync(window)
