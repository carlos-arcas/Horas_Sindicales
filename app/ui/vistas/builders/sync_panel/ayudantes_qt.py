from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QLabel, QPushButton

from app.ui.copy_catalog import copy_text
from app.ui.vistas.builders.sync_panel.bindings_senales import (
    conectar_evento_sync_panel,
)

if TYPE_CHECKING:
    from app.ui.vistas.main_window_vista import MainWindow


def crear_boton_accion(
    window: "MainWindow",
    clave_i18n: str,
    variante: str,
    nombre_handler: str,
    *,
    object_name: str | None = None,
    habilitado: bool = True,
) -> QPushButton:
    boton = QPushButton(copy_text(clave_i18n))
    boton.setProperty("variant", variante)
    if object_name:
        boton.setObjectName(object_name)
    boton.setEnabled(habilitado)
    conectar_evento_sync_panel(window, boton.clicked, nombre_handler)
    return boton


def crear_label_secundario(clave_i18n: str) -> QLabel:
    label = QLabel(copy_text(clave_i18n))
    label.setProperty("role", "secondary")
    return label
