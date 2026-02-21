from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CardWidget(QWidget):
    def __init__(self, titulo: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.title_label = QLabel(titulo)
        self.title_label.setProperty("role", "cardTitle")
        self.title_label.setVisible(bool(titulo))
        layout.addWidget(self.title_label)

    def set_titulo(self, titulo: str) -> None:
        self.title_label.setText(titulo)
        self.title_label.setVisible(bool(titulo))
