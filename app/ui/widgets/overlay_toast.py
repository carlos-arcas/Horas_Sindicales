from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget


class CapaToasts(QWidget):
    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self._host = host
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.hide()
        self.reposicionar()

    @property
    def layout_toasts(self) -> QVBoxLayout:
        return self._layout

    def reposicionar(self) -> None:
        self.setGeometry(self._host.rect())


__all__ = [CapaToasts.__name__]
