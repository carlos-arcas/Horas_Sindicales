from __future__ import annotations

from collections import deque
import logging
from typing import Callable

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtWidgets import QWidget

from app.ui.copy_catalog import copy_text
from app.ui.widgets.dialogo_detalles_toast import DialogoDetallesNotificacion
from app.ui.widgets.overlay_toast import CapaToasts
from app.ui.widgets.widget_toast import NotificacionToast, TarjetaToast

logger = logging.getLogger(__name__)


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

    def show(
        self,
        message: str | None = None,
        level: str = "info",
        title: str | None = None,
        *,
        action_label: str | None = None,
        action_callback: Callable[[], None] | None = None,
        details: str | None = None,
        correlation_id: str | None = None,
        code: str | None = None,
        duration_ms: int | None = None,
        **opts: object,
    ) -> None:
        notificacion = self._crear_notificacion(
            message=message,
            level=level,
            title=title,
            action_label=action_label,
            action_callback=action_callback,
            details=details,
            correlation_id=correlation_id,
            code=code,
            duration_ms=duration_ms,
            opts=opts,
        )
        if notificacion is None:
            return
        self.recibir_notificacion(notificacion)

    def _crear_notificacion(
        self,
        *,
        message: str | None,
        level: str,
        title: str | None,
        action_label: str | None,
        action_callback: Callable[[], None] | None,
        details: str | None,
        correlation_id: str | None,
        code: str | None,
        duration_ms: int | None,
        opts: dict[str, object],
    ) -> NotificacionToast | None:
        if message is None:
            return None
        details_value = self._resolver_campo_texto(details, opts, "details")
        code_value = self._resolver_campo_texto(code, opts, "code", "codigo")
        correlation_value = self._resolver_campo_texto(correlation_id, opts, "correlation_id", "correlacion_id")
        return NotificacionToast(
            id=str(id(message) + len(self._queue) + len(self._visibles)),
            titulo=title or copy_text("ui.toast.notificacion"),
            mensaje=message,
            nivel=level,
            detalles=details_value,
            codigo=code_value,
            correlacion_id=correlation_value,
            action_label=action_label if isinstance(action_label, str) else None,
            action_callback=action_callback,
            duracion_ms=8000 if duration_ms is None else max(0, int(duration_ms)),
        )

    def _resolver_campo_texto(self, valor: str | None, opts: dict[str, object], *claves: str) -> str | None:
        if isinstance(valor, str):
            return valor
        for clave in claves:
            extra = opts.get(clave)
            if isinstance(extra, str):
                return extra
        return None

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


__all__ = [GestorToasts.__name__]
