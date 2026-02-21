from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget


class PaginaSolicitudes(QWidget):
    def __init__(self, parent=None, content_widget: QWidget | None = None) -> None:
        super().__init__(parent)
        self._content_widget = content_widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if self._content_widget is not None:
            layout.addWidget(self._content_widget, 1)
