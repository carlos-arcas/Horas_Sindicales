from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from app.ui.widgets.toast_models import ToastDTO
from app.ui.copy_catalog import copy_text

_TOAST_LEVEL_ACCENTS = {
    "success": "#3FAF6A",
    "info": "#4C93F0",
    "warning": "#D09A34",
    "error": "#D35E5E",
}


class ToastWidget(QFrame):
    cerrado = Signal(str)
    solicitar_detalles = Signal(str)

    def __init__(self, dto: ToastDTO, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dto = dto
        self.setObjectName("toastWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.setMinimumWidth(360)
        self.setMaximumWidth(760)

        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 10, 10)
        root.setSpacing(6)

        title = QLabel(self.dto.titulo)
        title.setObjectName("toastTitle")
        title.setWordWrap(True)

        message = QLabel(self.dto.mensaje)
        message.setObjectName("toastMessage")
        message.setWordWrap(True)

        root.addWidget(title)
        root.addWidget(message)

        actions = QHBoxLayout()
        actions.addStretch(1)

        self._btn_detalles = QPushButton(copy_text("ui.sync.ver_detalles"))
        self._btn_detalles.setObjectName("toastDetailsButton")
        self._btn_detalles.clicked.connect(self._on_ver_detalles)
        visible = bool(self.dto.detalles or self.dto.correlacion_id)
        self._btn_detalles.setVisible(visible)
        actions.addWidget(self._btn_detalles)

        self._btn_cerrar = QPushButton(copy_text("ui.preferencias.cerrar"))
        self._btn_cerrar.setObjectName("toastCloseButton")
        self._btn_cerrar.clicked.connect(lambda: self.cerrado.emit(self.dto.id))
        actions.addWidget(self._btn_cerrar)

        root.addLayout(actions)

    def _on_ver_detalles(self) -> None:
        self.solicitar_detalles.emit(self.dto.id)

    def _apply_style(self) -> None:
        palette = QApplication.palette()
        bg = palette.window().color().lighter(106).name()
        text = palette.windowText().color().name()
        accent = _TOAST_LEVEL_ACCENTS.get(self.dto.nivel, _TOAST_LEVEL_ACCENTS["info"])
        accent_soft = QColor(accent).lighter(170).name()
        self.setStyleSheet(
            f"""
            QFrame#toastWidget {{
                background-color: {bg};
                border: 1px solid {accent_soft};
                border-left: 4px solid {accent};
                border-radius: 10px;
            }}
            QLabel#toastTitle {{
                color: {text};
                font-weight: 700;
            }}
            QLabel#toastMessage {{
                color: {text};
            }}
            QPushButton#toastCloseButton, QPushButton#toastDetailsButton {{
                padding: 3px 10px;
            }}
            """
        )
