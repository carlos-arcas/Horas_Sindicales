from __future__ import annotations

from PySide6.QtWidgets import QPushButton


class SecondaryButton(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setProperty("variant", "secondary")
        self.setProperty("role", "secondary")
