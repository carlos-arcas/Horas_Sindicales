from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PaginaHistorico(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Histórico")
        title.setProperty("role", "sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel("Consulta historial de solicitudes y trazabilidad de operaciones.")
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "secondary")
        layout.addWidget(subtitle)

        info = QLabel("Usa esta vista para navegar registros consolidados y validar acciones previas.")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch(1)
