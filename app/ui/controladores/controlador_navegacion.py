from __future__ import annotations

from PySide6.QtWidgets import QListWidget, QStackedWidget


class ControladorNavegacion:
    def __init__(self, sidebar: QListWidget, paginas: QStackedWidget) -> None:
        self._sidebar = sidebar
        self._paginas = paginas
        self._sidebar.currentRowChanged.connect(self.cambiar_pagina)

    def cambiar_pagina(self, index: int) -> None:
        if 0 <= index < self._paginas.count():
            self._paginas.setCurrentIndex(index)
