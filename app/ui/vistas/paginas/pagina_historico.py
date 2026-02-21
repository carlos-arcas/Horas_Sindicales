from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.ui.components.empty_state import EmptyStateWidget


class PaginaHistorico(QWidget):
    ver_solicitudes = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        self.empty_state = EmptyStateWidget(
            titulo="No hay historial todavía",
            descripcion="Cuando confirmes solicitudes podrás revisar aquí la trazabilidad completa.",
            accion_texto="Ver solicitudes",
            on_action=self.ver_solicitudes.emit,
        )
        layout.addWidget(self.empty_state)
