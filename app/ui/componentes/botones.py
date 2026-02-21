from __future__ import annotations

from PySide6.QtWidgets import QPushButton


class BotonPrimario(QPushButton):
    def __init__(self, texto: str, parent=None) -> None:
        super().__init__(texto, parent)
        self.setProperty("variant", "primary")


class BotonSecundario(QPushButton):
    def __init__(self, texto: str, parent=None) -> None:
        super().__init__(texto, parent)
        self.setProperty("variant", "secondary")
