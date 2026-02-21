from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PaginaConfiguracion(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Configuración")
        title.setProperty("role", "sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel("Administra parámetros de aplicación y preferencias de uso.")
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "secondary")
        layout.addWidget(subtitle)

        info = QLabel("Esta página centraliza ajustes generales manteniendo una navegación lateral consistente.")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch(1)
