from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.ui.components.empty_state import EmptyStateWidget


class PaginaConfiguracion(QWidget):
    editar_grupo = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        self.empty_state = EmptyStateWidget(
            titulo="Ajustes de la aplicación",
            descripcion="Centraliza la configuración de uso diario sin exponer opciones técnicas innecesarias.",
            accion_texto="Editar grupo",
            on_action=self.editar_grupo.emit,
        )
        layout.addWidget(self.empty_state)
