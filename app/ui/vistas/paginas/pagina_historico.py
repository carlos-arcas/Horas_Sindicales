from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.ui.components.empty_state import EmptyStateWidget


class PaginaHistorico(QWidget):
    ver_solicitudes = Signal()
    sincronizar = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        self.empty_state = EmptyStateWidget(
            titulo="No hay historial todavía",
            descripcion="Cuando confirmes solicitudes podrás revisar aquí la trazabilidad completa.",
            accion_primaria_texto="Crear primera solicitud",
            on_accion_primaria=self.ver_solicitudes.emit,
            accion_secundaria_texto="Sincronizar",
            on_accion_secundaria=self.sincronizar.emit,
        )
        layout.addWidget(self.empty_state)
