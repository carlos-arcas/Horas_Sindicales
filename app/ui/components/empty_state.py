from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class EmptyStateWidget(QWidget):
    def __init__(
        self,
        titulo: str,
        descripcion: str,
        accion_texto: str | None = None,
        on_action: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)

        icono = QLabel("🗂️")
        icono.setProperty("role", "title")
        layout.addWidget(icono)

        titulo_label = QLabel(titulo)
        titulo_label.setProperty("role", "sectionTitle")
        titulo_label.setWordWrap(True)
        layout.addWidget(titulo_label)

        descripcion_label = QLabel(descripcion)
        descripcion_label.setProperty("role", "secondary")
        descripcion_label.setWordWrap(True)
        layout.addWidget(descripcion_label)

        if accion_texto:
            self.accion_button = QPushButton(accion_texto)
            self.accion_button.setProperty("variant", "secondary")
            if on_action is not None:
                self.accion_button.clicked.connect(on_action)
            layout.addWidget(self.accion_button)
        else:
            self.accion_button = None

        layout.addStretch(1)
