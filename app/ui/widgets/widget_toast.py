from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from app.ui.copy_catalog import copy_text
from app.ui.estilos.cargador_estilos_notificaciones import construir_estilo_tarjeta_toast
from app.ui.toasts.ejecutar_callback_seguro import ejecutar_callback_seguro
from app.ui.toasts.toast_actions import cerrar_toast

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
    origen: str | None = None
    action_label: str | None = None
    action_callback: Callable[[], None] | None = None
    dedupe_key: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().strftime(copy_text("ui.toast.fecha_formato_default")))
    duracion_ms: int = 8000


class TarjetaToast(QFrame):
    cerrado = Signal(str)
    solicitar_detalles = Signal(str)
    _ACENTOS_NIVEL = {"success": "#3FAF6A", "info": "#4C93F0", "warning": "#D09A34", "error": "#D35E5E"}
    _FONDO_NIVEL = {"success": "#EAF8EF", "info": "#EAF3FF", "warning": "#FFF6E6", "error": "#FDECEC"}

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
        self._label_titulo = titulo
        titulo.setObjectName("toastTitle")
        titulo.setWordWrap(True)
        mensaje = QLabel(self.notificacion.mensaje)
        self._label_mensaje = mensaje
        mensaje.setObjectName("toastMessage")
        mensaje.setWordWrap(True)
        root.addWidget(titulo)
        root.addWidget(mensaje)
        acciones = QHBoxLayout()
        acciones.addStretch(1)
        self._acciones_layout = acciones
        self._btn_detalles: QPushButton | None = None
        self._asegurar_boton_detalles()
        self._sincronizar_boton_detalles()
        self._btn_accion = QPushButton(self.notificacion.action_label or "")
        self._btn_accion.setObjectName("toastActionButton")
        self._btn_accion.clicked.connect(self._ejecutar_accion)
        has_action_label = bool(self.notificacion.action_label)
        self._btn_accion.setVisible(has_action_label)
        self._btn_accion.setEnabled(self.notificacion.action_callback is not None)
        acciones.addWidget(self._btn_accion)
        self._btn_cerrar = QPushButton(copy_text("ui.toast.cerrar"))
        self._btn_cerrar.setObjectName("toastCloseButton")
        self._btn_cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cerrar.setToolTip(copy_text("ui.toast.cerrar_hint"))
        self._btn_cerrar.clicked.connect(self._on_close_clicked)
        acciones.addWidget(self._btn_cerrar)
        root.addLayout(acciones)

    def _on_close_clicked(self) -> None:
        logger.info(
            "TOAST_MANUAL_CLOSE",
            extra={
                "toast_id": self.notificacion.id,
                "nivel": self.notificacion.nivel,
                "correlation_id": self.notificacion.correlacion_id,
            },
        )
        cerrar_toast(self, self.notificacion.id)

    def actualizar_notificacion(self, notificacion: NotificacionToast) -> None:
        self.notificacion = notificacion
        self._label_titulo.setText(notificacion.titulo)
        self._label_mensaje.setText(notificacion.mensaje)
        self._btn_accion.setText(notificacion.action_label or "")
        has_action_label = bool(notificacion.action_label)
        self._btn_accion.setVisible(has_action_label)
        self._btn_accion.setEnabled(notificacion.action_callback is not None)
        self._sincronizar_boton_detalles()

    def _asegurar_boton_detalles(self) -> None:
        if self._btn_detalles is not None:
            return
        self._btn_detalles = QPushButton(copy_text("ui.sync.ver_detalles"))
        self._btn_detalles.setObjectName("toastDetailsButton")
        self._btn_detalles.clicked.connect(self._emitir_solicitud_detalles)
        self._acciones_layout.insertWidget(1, self._btn_detalles)

    def _emitir_solicitud_detalles(self) -> None:
        self.solicitar_detalles.emit(self.notificacion.id)

    def _sincronizar_boton_detalles(self) -> None:
        self._asegurar_boton_detalles()
        hay_detalles = bool(self.notificacion.detalles)
        self._btn_detalles.setVisible(hay_detalles)

    def _ejecutar_accion(self) -> None:
        logger.info(
            "TOAST_ACTION_CLICK",
            extra={
                "titulo": self.notificacion.titulo,
                "mensaje": self.notificacion.mensaje,
                "correlation_id": self.notificacion.correlacion_id,
            },
        )
        ejecutar_callback_seguro(
            self.notificacion.action_callback,
            logger=logger,
            contexto=f"toast:{self.notificacion.nivel}:{self.notificacion.action_label or 'sin_accion'}",
            correlation_id=self.notificacion.correlacion_id,
        )

    def _apply_style(self) -> None:
        palette = QApplication.palette()
        text = palette.windowText().color().name()
        accent = self._ACENTOS_NIVEL.get(self.notificacion.nivel, self._ACENTOS_NIVEL["info"])
        bg = self._FONDO_NIVEL.get(self.notificacion.nivel, self._FONDO_NIVEL["info"])
        accent_soft = QColor(accent).lighter(165).name()
        close_hover = QColor(accent).lighter(185).name()
        close_pressed = QColor(accent).lighter(155).name()
        estilo = construir_estilo_tarjeta_toast(
            color_texto=text,
            color_acento=accent,
            color_acento_suave=accent_soft,
            color_fondo=bg,
            color_cerrar_hover=close_hover,
            color_cerrar_pressed=close_pressed,
        )
        self.setStyleSheet(estilo)


Toast = TarjetaToast

__all__ = [NotificacionToast.__name__, TarjetaToast.__name__, Toast.__name__]
