from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
import logging

from PySide6.QtCore import QEvent, QObject, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

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
    timestamp: str = field(default_factory=lambda: datetime.now().strftime(copy_text("ui.toast.fecha_formato_default")))
    duracion_ms: int = 8000


class DialogoDetallesNotificacion(QDialog):
    def __init__(self, notificacion: NotificacionToast, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._notificacion = notificacion
        self.setWindowTitle(copy_text("ui.toast.detalles_notificacion"))
        self.setModal(True)
        self.resize(560, 420)

        root = QVBoxLayout(self)
        for line in self._lineas_resumen():
            label = QLabel(line)
            label.setWordWrap(True)
            root.addWidget(label)

        self._detalles = QTextEdit()
        self._detalles.setReadOnly(True)
        self._detalles.setPlainText(self._construir_texto())
        root.addWidget(self._detalles, 1)

        acciones = QHBoxLayout()
        self._btn_copiar = QPushButton(copy_text("ui.toast.copiar"))
        self._btn_cerrar = QPushButton(copy_text("ui.preferencias.cerrar"))
        self._btn_copiar.clicked.connect(self._copiar_al_portapapeles)
        self._btn_cerrar.clicked.connect(self.accept)
        acciones.addStretch(1)
        acciones.addWidget(self._btn_copiar)
        acciones.addWidget(self._btn_cerrar)
        root.addLayout(acciones)

    def _lineas_resumen(self) -> list[str]:
        return [
            f"{copy_text('ui.toast.titulo')} {self._notificacion.titulo}",
            f"{copy_text('ui.toast.mensaje')} {self._notificacion.mensaje}",
            f"{copy_text('ui.toast.codigo')} {self._notificacion.codigo or copy_text('ui.toast.no_disponible')}",
            f"{copy_text('ui.toast.correlacion')} {self._notificacion.correlacion_id or copy_text('ui.toast.no_disponible')}",
            f"{copy_text('ui.toast.fecha_hora')} {self._notificacion.timestamp}",
        ]

    def _construir_texto(self) -> str:
        bloques = [
            f"{copy_text('ui.toast.titulo')} {self._notificacion.titulo}",
            f"{copy_text('ui.toast.mensaje')} {self._notificacion.mensaje}",
            f"{copy_text('ui.toast.detalles')} {self._notificacion.detalles or copy_text('ui.toast.no_disponible')}",
            f"{copy_text('ui.toast.codigo')} {self._notificacion.codigo or copy_text('ui.toast.no_disponible')}",
            f"{copy_text('ui.toast.correlacion')} {self._notificacion.correlacion_id or copy_text('ui.toast.no_disponible')}",
            f"{copy_text('ui.toast.timestamp')} {self._notificacion.timestamp}",
        ]
        return "\n".join(bloques)

    def _copiar_al_portapapeles(self) -> None:
        QGuiApplication.clipboard().setText(self._construir_texto())


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
        self._btn_cerrar = QPushButton(copy_text("ui.preferencias.cerrar"))
        self._btn_cerrar.setObjectName("toastCloseButton")
        self._btn_cerrar.clicked.connect(lambda: self.cerrado.emit(self.notificacion.id))
        acciones.addWidget(self._btn_cerrar)
        root.addLayout(acciones)

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
            QPushButton#toastCloseButton, QPushButton#toastDetailsButton {{ padding: 3px 10px; }}
            """
        )


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


class GestorToasts(QObject):
    def __init__(self, parent: QWidget | None = None, *, max_visibles: int = 3) -> None:
        super().__init__(parent)
        self._host: QWidget | None = parent
        self._overlay: CapaToasts | None = None
        self._max_visibles = max(1, int(max_visibles))
        self._visibles: dict[str, TarjetaToast] = {}
        self._timers: dict[str, QTimer] = {}
        self._queue: deque[NotificacionToast] = deque()
        self._cache: dict[str, NotificacionToast] = {}
        self._is_active = False

    def attach_to(self, main_window: QWidget) -> None:
        self._detach_host()
        self._host = main_window
        self._overlay = CapaToasts(main_window)
        self._overlay.show()
        self._is_active = True
        main_window.installEventFilter(self)

    def conectar_adaptador(self, adaptador: object, signal_name: str = "toast_requested") -> bool:
        signal = getattr(adaptador, signal_name, None)
        if signal is None or not hasattr(signal, "connect"):
            return False
        signal.connect(self.recibir_notificacion)  # type: ignore[attr-defined]
        return True

    def show(self, message: str | None = None, level: str = "info", title: str | None = None, duration_ms: int | None = None, **opts: object) -> None:
        if message is None:
            return
        notificacion = NotificacionToast(
            id=str(id(message) + len(self._queue) + len(self._visibles)),
            titulo=title or copy_text("ui.toast.notificacion"),
            mensaje=message,
            nivel=level,
            detalles=opts.get("details") if isinstance(opts.get("details"), str) else None,
            codigo=opts.get("codigo") if isinstance(opts.get("codigo"), str) else None,
            correlacion_id=opts.get("correlacion_id") if isinstance(opts.get("correlacion_id"), str) else None,
            duracion_ms=8000 if duration_ms is None else max(0, int(duration_ms)),
        )
        self.recibir_notificacion(notificacion)

    def success(self, message: str, title: str | None = None, duration_ms: int | None = None, **opts: object) -> None:
        self.show(message=message, level="success", title=title, duration_ms=duration_ms, **opts)

    def info(self, message: str, title: str | None = None, duration_ms: int | None = None, **opts: object) -> None:
        self.show(message=message, level="info", title=title, duration_ms=duration_ms, **opts)

    def warning(self, message: str, title: str | None = None, duration_ms: int | None = None, **opts: object) -> None:
        self.show(message=message, level="warning", title=title, duration_ms=duration_ms, **opts)

    def error(self, message: str, title: str | None = None, duration_ms: int | None = None, **opts: object) -> None:
        details = opts.get("details")
        payload_message = f"{message}\n{details}" if isinstance(details, str) and details else message
        self.show(message=payload_message, level="error", title=title, duration_ms=duration_ms, **opts)

    def recibir_notificacion(self, notificacion: NotificacionToast) -> None:
        if not self._is_active or self._overlay is None:
            logger.warning("GestorToasts no activo. Toast descartado: %s", notificacion.mensaje)
            return
        self._cache[notificacion.id] = notificacion
        if len(self._visibles) < self._max_visibles:
            self._mostrar(notificacion)
            return
        self._queue.append(notificacion)

    def _mostrar(self, notificacion: NotificacionToast) -> None:
        if self._overlay is None:
            return
        tarjeta = TarjetaToast(notificacion, parent=self._overlay)
        tarjeta.cerrado.connect(self._cerrar_toast)
        tarjeta.solicitar_detalles.connect(self._abrir_detalles)
        self._overlay.layout_toasts.addWidget(tarjeta, 0, Qt.AlignmentFlag.AlignHCenter)
        self._overlay.show()
        tarjeta.show()
        self._visibles[notificacion.id] = tarjeta
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda toast_id=notificacion.id: self._cerrar_toast(toast_id))
        timer.start(max(0, int(notificacion.duracion_ms or 8000)))
        self._timers[notificacion.id] = timer

    def _cerrar_toast(self, toast_id: str) -> None:
        timer = self._timers.pop(toast_id, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
        tarjeta = self._visibles.pop(toast_id, None)
        if tarjeta is not None:
            tarjeta.hide()
            tarjeta.deleteLater()
        if self._queue:
            self._mostrar(self._queue.popleft())
        elif self._overlay is not None and not self._visibles:
            self._overlay.hide()

    def _abrir_detalles(self, toast_id: str) -> None:
        notificacion = self._cache.get(toast_id)
        if notificacion is None or self._host is None:
            return
        DialogoDetallesNotificacion(notificacion, parent=self._host).exec()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if self._host is not None and watched is self._host and event.type() in (QEvent.Resize, QEvent.Move):
            if self._overlay is not None:
                self._overlay.reposicionar()
        return super().eventFilter(watched, event)

    def _detach_host(self) -> None:
        if self._host is not None:
            self._host.removeEventFilter(self)
        for toast_id in list(self._visibles.keys()):
            self._cerrar_toast(toast_id)
        self._queue.clear()
        if self._overlay is not None:
            self._overlay.hide()
            self._overlay.deleteLater()
            self._overlay = None
        self._host = None
        self._is_active = False

    def show_toast(self, message: str, level: str = "info", title: str | None = None, duration_ms: int | None = None) -> None:
        self.show(message=message, level=level, title=title, duration_ms=duration_ms)

    def add_toast(self, message: str, level: str = "info", title: str | None = None, duration_ms: int | None = None) -> None:
        self.show_toast(message=message, level=level, title=title, duration_ms=duration_ms)


Toast = TarjetaToast

def _on_action_clicked() -> None:
    return None

# action_button.clicked.connect(self._on_action_clicked)
__all__ = [Toast.__name__, NotificacionToast.__name__, GestorToasts.__name__, TarjetaToast.__name__]
