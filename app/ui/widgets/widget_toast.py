from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from app.ui.copy_catalog import copy_text

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NotificacionToast:
    id: str
    titulo: str
    mensaje: str
    nivel: str = "info"
    detalles: str | None = None
    codigo: str | None = None
    correlacion_id: str | None = None
    action_label: str | None = None
    action_callback: Callable[[], None] | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().strftime(copy_text("ui.toast.fecha_formato_default")))
    duracion_ms: int = 8000


class TarjetaToast(QFrame):
    cerrado = Signal(str)
    solicitar_detalles = Signal(str)
    _ACENTOS_NIVEL = {"success": "#3FAF6A", "info": "#4C93F0", "warning": "#D09A34", "error": "#D35E5E"}

    def __init__(self, notificacion: NotificacionToast, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.notificacion = notificacion
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
        titulo = QLabel(self.notificacion.titulo)
        titulo.setObjectName("toastTitle")
        titulo.setWordWrap(True)
        mensaje = QLabel(self.notificacion.mensaje)
        mensaje.setObjectName("toastMessage")
        mensaje.setWordWrap(True)
        root.addWidget(titulo)
        root.addWidget(mensaje)
        acciones = QHBoxLayout()
        acciones.addStretch(1)
        self._btn_detalles = QPushButton(copy_text("ui.sync.ver_detalles"))
        self._btn_detalles.setObjectName("toastDetailsButton")
        self._btn_detalles.clicked.connect(lambda: self.solicitar_detalles.emit(self.notificacion.id))
        self._btn_detalles.setVisible(bool(self.notificacion.detalles or self.notificacion.correlacion_id))
        acciones.addWidget(self._btn_detalles)
        self._btn_accion = QPushButton(self.notificacion.action_label or "")
        self._btn_accion.setObjectName("toastActionButton")
        self._btn_accion.clicked.connect(self._ejecutar_accion)
        has_action_label = bool(self.notificacion.action_label)
        self._btn_accion.setVisible(has_action_label)
        self._btn_accion.setEnabled(self.notificacion.action_callback is not None)
        acciones.addWidget(self._btn_accion)
        self._btn_cerrar = QPushButton(copy_text("ui.preferencias.cerrar"))
        self._btn_cerrar.setObjectName("toastCloseButton")
        self._btn_cerrar.clicked.connect(lambda: self.cerrado.emit(self.notificacion.id))
        acciones.addWidget(self._btn_cerrar)
        root.addLayout(acciones)

    def _ejecutar_accion(self) -> None:
        callback = self.notificacion.action_callback
        if callback is None:
            return
        try:
            callback()
        except Exception:
            logger.exception(
                "toast_action_callback_failed",
                extra={
                    "toast_id": self.notificacion.id,
                    "toast_level": self.notificacion.nivel,
                    "toast_action_label": self.notificacion.action_label,
                },
            )

    def _apply_style(self) -> None:
        palette = QApplication.palette()
        bg = palette.window().color().lighter(106).name()
        text = palette.windowText().color().name()
        accent = self._ACENTOS_NIVEL.get(self.notificacion.nivel, self._ACENTOS_NIVEL["info"])
        accent_soft = QColor(accent).lighter(170).name()
        self.setStyleSheet(
            f"""
            QFrame#toastWidget {{ background-color: {bg}; border: 1px solid {accent_soft}; border-left: 4px solid {accent}; border-radius: 10px; }}
            QLabel#toastTitle {{ color: {text}; font-weight: 700; }}
            QLabel#toastMessage {{ color: {text}; }}
            QPushButton#toastCloseButton, QPushButton#toastDetailsButton, QPushButton#toastActionButton {{ padding: 3px 10px; }}
            """
        )


Toast = TarjetaToast

__all__ = [NotificacionToast.__name__, TarjetaToast.__name__, Toast.__name__]
