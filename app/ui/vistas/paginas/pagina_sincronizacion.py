from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.ui.components.empty_state import EmptyStateWidget


class PaginaSincronizacion(QWidget):
    configurar_credenciales = Signal()
    sincronizar = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        self.empty_state = EmptyStateWidget(
            titulo="Aún no has sincronizado",
            descripcion="Conecta Google Sheets para empezar a sincronizar solicitudes y detectar conflictos.",
            accion_primaria_texto="Sincronizar ahora",
            on_accion_primaria=self.sincronizar.emit,
            accion_secundaria_texto="Configurar credenciales",
            on_accion_secundaria=self.configurar_credenciales.emit,
        )
        layout.addWidget(self.empty_state)
