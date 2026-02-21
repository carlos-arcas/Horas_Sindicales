from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class CabeceraPagina(QWidget):
    def __init__(self, titulo: str, subtitulo: str = "", parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        text = QVBoxLayout()
        self.titulo = QLabel(titulo)
        self.subtitulo = QLabel(subtitulo)
        self.subtitulo.setProperty("role", "secondary")
        text.addWidget(self.titulo)
        text.addWidget(self.subtitulo)
        layout.addLayout(text)
        layout.addStretch(1)

from PySide6.QtWidgets import QVBoxLayout
