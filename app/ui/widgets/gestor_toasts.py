from __future__ import annotations

from collections import deque
from dataclasses import replace
import logging
import sys
from time import monotonic
import traceback
from typing import Callable

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtWidgets import QWidget

from app.ui.copy_catalog import copy_text
from app.ui.toasts.modelo_toast import GestorToasts as GestorToastsModelo
from app.ui.toasts.modelo_toast import ToastModelo
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
        if message is None:
            return None
        details_value = self._resolver_campo_texto(details, opts, "details")
        code_value = self._resolver_campo_texto(code, opts, "code", "codigo") or "SIN_CODIGO"
        origin_value = self._resolver_campo_texto(origin, opts, "origin", "origen") or "origen_desconocido"
        correlation_value = self._resolver_campo_texto(correlation_id, opts, "correlation_id", "correlacion_id")
        detalles_completos, tipo_excepcion = self._resolver_detalles(details_value, exc_info)
        dedupe_key = self._crear_dedupe_key(code_value, origin_value, tipo_excepcion)
        toast_id = f"{dedupe_key}:{int(monotonic() * 1000)}"
        notificacion = NotificacionToast(
            id=toast_id,
            titulo=title or copy_text("ui.toast.notificacion"),
            mensaje=message,
            nivel=level,
            detalles=detalles_completos,
            codigo=code_value,
            correlacion_id=correlation_value,
            origen=origin_value,
            action_label=action_label if isinstance(action_label, str) else None,
            action_callback=action_callback,
            dedupe_key=dedupe_key,
            duracion_ms=8000 if duration_ms is None else max(0, int(duration_ms)),
        )
        logger.info(
            "TOAST_PAYLOAD_BUILD",
            extra={
                "toast_id": notificacion.id,
                "dedupe_key": notificacion.dedupe_key,
                "nivel": notificacion.nivel,
                "codigo": notificacion.codigo,
                "origen": notificacion.origen,
            },
        )
        return notificacion

    def _resolver_detalles(
        self,
        detalles: str | None,
        exc_info: BaseException | tuple[type[BaseException], BaseException, object] | bool | None,
    ) -> tuple[str | None, str | None]:
        if isinstance(exc_info, tuple) and exc_info and isinstance(exc_info[0], type):
            return "".join(traceback.format_exception(*exc_info)), exc_info[0].__name__
        if isinstance(exc_info, BaseException):
            return "".join(traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__)), type(exc_info).__name__
        if exc_info is True:
            clase, valor, tb = sys.exc_info()
            if clase is not None and valor is not None:
                return "".join(traceback.format_exception(clase, valor, tb)), clase.__name__
        return detalles, None

    def _crear_dedupe_key(self, codigo: str, origen: str, tipo_excepcion: str | None) -> str:
        return f"{codigo}:{origen}:{tipo_excepcion or 'sin_excepcion'}"

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
