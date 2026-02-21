from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PaginaSolicitudes(QWidget):
    def __init__(self, parent=None, content_widget: QWidget | None = None) -> None:
        super().__init__(parent)
        self._content_widget = content_widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Solicitudes")
        title.setProperty("role", "sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel("Gestiona la operativa diaria de solicitudes con una vista clara y consistente.")
        subtitle.setWordWrap(True)
        subtitle.setProperty("role", "secondary")
        layout.addWidget(subtitle)

        if self._content_widget is not None:
            layout.addWidget(self._content_widget, 1)
