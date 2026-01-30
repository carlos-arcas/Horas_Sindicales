from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class HeaderWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        self.logo_label = QLabel()
        self.logo_label.setObjectName("headerLogo")
        self.logo_label.setFixedHeight(56)
        self.logo_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.logo_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._set_logo_pixmap()

        title_block = QWidget()
        title_layout = QVBoxLayout(title_block)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        title = QLabel("Horas Sindicales")
        title.setProperty("role", "title")
        subtitle = QLabel("Gestión de solicitudes y saldos")
        subtitle.setProperty("role", "subtitle")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        layout.addWidget(self.logo_label)
        layout.addWidget(title_block)
        layout.addStretch(1)

    def _set_logo_pixmap(self) -> None:
        root = Path(__file__).resolve().parents[3]
        candidates = [root / "logo.png", root / "assets" / "logo.png"]
        for candidate in candidates:
            if candidate.exists():
                pixmap = QPixmap(str(candidate))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        160,
                        56,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    self.logo_label.setPixmap(scaled)
                    return
        self.logo_label.setText("CGT")
        self.logo_label.setProperty("role", "badge")
