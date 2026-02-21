from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PaginaSincronizacion(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Sincronización")
        title.setProperty("role", "sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Supervisa el estado de integración con Google Sheets y ejecuta sincronizaciones de forma segura."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "secondary")
        layout.addWidget(subtitle)

        info = QLabel("Selecciona esta sección para revisar resultados, reintentos y conflictos de sincronización.")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch(1)
