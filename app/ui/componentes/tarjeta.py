from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget


class Tarjeta(QFrame):
    def __init__(self, contenido: QWidget | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("card", "true")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        if contenido is not None:
            layout.addWidget(contenido)
