from __future__ import annotations

from collections import deque
from dataclasses import replace
import logging
from time import monotonic
from typing import Callable

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtWidgets import QWidget

from app.ui.toasts.modelo_toast import GestorToasts as GestorToastsModelo
from app.ui.toasts.modelo_toast import ToastModelo
from app.ui.widgets.dialogo_detalles_toast import DialogoDetallesNotificacion
from app.ui.widgets.overlay_toast import CapaToasts
from app.ui.toasts.toast_payload_builder import ToastPayloadEntrada, construir_toast_payload
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
        self._modelo = GestorToastsModelo(max_toasts=self._max_visibles)
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
        origin: str | None = None,
        exc_info: BaseException | tuple[type[BaseException], BaseException, object] | bool | None = None,
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
            origin=origin,
            exc_info=exc_info,
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
        origin: str | None,
        exc_info: BaseException | tuple[type[BaseException], BaseException, object] | bool | None,
        duration_ms: int | None,
        opts: dict[str, object],
    ) -> NotificacionToast | None:
        notificacion = construir_toast_payload(
            ToastPayloadEntrada(
                message=message,
                level=level,
                title=title,
                action_label=action_label,
                action_callback=action_callback,
                details=details,
                correlation_id=correlation_id,
                code=code,
                origin=origin,
                exc_info=exc_info,
                duration_ms=duration_ms,
                opts=opts,
            )
        )
        if notificacion is None:
            return None
        dto = NotificacionToast(
            id=notificacion.toast_id,
            titulo=notificacion.titulo,
            mensaje=notificacion.mensaje,
            nivel=notificacion.nivel,
            detalles=notificacion.detalles,
            codigo=notificacion.codigo,
            correlacion_id=notificacion.correlacion_id,
            origen=notificacion.origen,
            action_label=notificacion.action_label,
            action_callback=notificacion.action_callback,
            dedupe_key=notificacion.dedupe_key,
            duracion_ms=notificacion.duracion_ms,
        )
        logger.info(
            "TOAST_PAYLOAD_BUILD",
            extra={
                "toast_id": dto.id,
                "dedupe_key": dto.dedupe_key,
                "nivel": dto.nivel,
                "codigo": dto.codigo,
                "origen": dto.origen,
            },
        )
        return dto

    def recibir_notificacion(self, notificacion: NotificacionToast) -> None:
        if not self._is_active or self._overlay is None:
            logger.warning("GestorToasts no activo. Toast descartado: %s", notificacion.mensaje)
            return
        modelo = ToastModelo(
            id=notificacion.id,
            tipo=notificacion.nivel if notificacion.nivel in {"info", "success", "warning", "error"} else "info",
            titulo=notificacion.titulo,
            mensaje=notificacion.mensaje,
            detalles=notificacion.detalles,
            dedupe_key=notificacion.dedupe_key,
            created_at_monotonic=monotonic(),
            updated_at_monotonic=monotonic(),
        )
        previo_ids = [toast.id for toast in self._modelo.listar()]
        resultado = self._modelo.agregar_toast(modelo)
        actuales_ids = [toast.id for toast in self._modelo.listar()]

        if resultado.id in self._visibles:
            notificacion_actualizada = replace(notificacion, id=resultado.id)
            self._cache[resultado.id] = notificacion_actualizada
            self._visibles[resultado.id].actualizar_notificacion(notificacion_actualizada)
            logger.info(
                "TOAST_DEDUPE_UPDATE",
                extra={
                    "toast_id": resultado.id,
                    "dedupe_key": notificacion_actualizada.dedupe_key,
                    "nivel": notificacion_actualizada.nivel,
                },
            )
            return

        ids_eliminados = [toast_id for toast_id in previo_ids if toast_id not in actuales_ids]
        for toast_id in ids_eliminados:
            self._cerrar_toast(toast_id)

        if notificacion.nivel == "error":
            logger.error(
                "UI_TOAST_ERROR_SHOWN",
                extra={
                    "codigo": notificacion.codigo or "SIN_CODIGO",
                    "dedupe_key": notificacion.dedupe_key,
                    "origen": notificacion.origen or "origen_desconocido",
                },
            )

        self._cache[notificacion.id] = notificacion
        if len(self._visibles) < self._max_visibles:
            self._mostrar(notificacion)
            return
        if self._visibles:
            antiguo_id = next(iter(self._visibles.keys()))
            self._cerrar_toast(antiguo_id)
        self._mostrar(notificacion)

    def _mostrar(self, notificacion: NotificacionToast) -> None:
        if self._overlay is None:
            return
        logger.info(
            "TOAST_RENDER",
            extra={
                "toast_id": notificacion.id,
                "dedupe_key": notificacion.dedupe_key,
                "nivel": notificacion.nivel,
            },
        )
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
        self._modelo.cerrar_toast(toast_id)
        self._cache.pop(toast_id, None)
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
