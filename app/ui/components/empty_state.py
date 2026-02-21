from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class EmptyStateWidget(QWidget):
    def __init__(
        self,
        titulo: str,
        descripcion: str,
        accion_primaria_texto: str | None = None,
        on_accion_primaria: Callable[[], None] | None = None,
        accion_secundaria_texto: str | None = None,
        on_accion_secundaria: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

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

        acciones_layout = QHBoxLayout()
        acciones_layout.setSpacing(10)

        self.accion_primaria_button: QPushButton | None = None
        if accion_primaria_texto:
            self.accion_primaria_button = QPushButton(accion_primaria_texto)
            self.accion_primaria_button.setProperty("variant", "primary")
            if on_accion_primaria is not None:
                self.accion_primaria_button.clicked.connect(on_accion_primaria)
            acciones_layout.addWidget(self.accion_primaria_button)

        self.accion_secundaria_button: QPushButton | None = None
        if accion_secundaria_texto:
            self.accion_secundaria_button = QPushButton(accion_secundaria_texto)
            self.accion_secundaria_button.setProperty("variant", "secondary")
            if on_accion_secundaria is not None:
                self.accion_secundaria_button.clicked.connect(on_accion_secundaria)
            acciones_layout.addWidget(self.accion_secundaria_button)

        if self.accion_primaria_button is not None or self.accion_secundaria_button is not None:
            acciones_layout.addStretch(1)
            layout.addLayout(acciones_layout)

        layout.addStretch(1)
