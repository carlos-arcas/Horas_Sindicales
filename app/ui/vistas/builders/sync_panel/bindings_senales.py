from __future__ import annotations

from typing import TYPE_CHECKING

from app.ui.copy_catalog import copy_text
from app.ui.vistas.main_window.wiring_helpers import conectar_signal

if TYPE_CHECKING:
    from PySide6.QtCore import SignalInstance

    from app.ui.vistas.main_window_vista import MainWindow


CONTEXTO_SYNC_PANEL = copy_text("ui.debug.builders_sync_panel")


def conectar_evento_sync_panel(window: "MainWindow", signal: "SignalInstance", handler: str) -> None:
    conectar_signal(window, signal, handler, contexto=CONTEXTO_SYNC_PANEL)
