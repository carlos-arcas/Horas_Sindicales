from __future__ import annotations

from collections import deque
from collections.abc import Callable
import logging

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtWidgets import QWidget

from app.ui.widgets.dialogo_detalles_toast import DialogoDetallesToast
from app.ui.widgets.toast_models import ToastDTO
from app.ui.widgets.toast_overlay import ToastOverlay
from app.ui.widgets.toast_widget import ToastWidget

logger = logging.getLogger(__name__)


class ToastManager(QObject):
    def __init__(self, parent: QWidget | None = None, *, max_visibles: int = 3) -> None:
        super().__init__(parent)
        self._host: QWidget | None = parent
        self._overlay: ToastOverlay | None = None
        self._max_visibles = max(1, int(max_visibles))
        self._visibles: dict[str, ToastWidget] = {}
        self._timers: dict[str, QTimer] = {}
        self._queue: deque[ToastDTO] = deque()
        self._cache: dict[str, ToastDTO] = {}
        self._is_active = False

    def attach_to(self, main_window: QWidget) -> None:
        self._detach_host()
        self._host = main_window
        self._overlay = ToastOverlay(main_window)
        self._overlay.show()
        self._is_active = True
        main_window.installEventFilter(self)

    def conectar_adapter(self, adapter: object, signal_name: str = "toast_requested") -> bool:
        signal = getattr(adapter, signal_name, None)
        if signal is None or not hasattr(signal, "connect"):
            return False
        signal.connect(self.recibir_dto)  # type: ignore[attr-defined]
        return True

    def show(
        self,
        message: str | None = None,
        level: str = "info",
        title: str | None = None,
        duration_ms: int | None = None,
        **opts: object,
    ) -> None:
        if message is None:
            return
        dto = ToastDTO(
            id=str(id(message) + len(self._queue) + len(self._visibles)),
            titulo=title or "Notificación",
            mensaje=message,
            nivel=level,
            detalles=opts.get("details") if isinstance(opts.get("details"), str) else None,
            codigo=opts.get("codigo") if isinstance(opts.get("codigo"), str) else None,
            correlacion_id=(opts.get("correlacion_id") if isinstance(opts.get("correlacion_id"), str) else None),
            duracion_ms=8000 if duration_ms is None else max(0, int(duration_ms)),
        )
        self.recibir_dto(dto)

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

    def recibir_dto(self, dto: ToastDTO) -> None:
        if not self._is_active or self._overlay is None:
            logger.warning("ToastManager no activo. Toast descartado: %s", dto.mensaje)
            return
        self._cache[dto.id] = dto
        if len(self._visibles) < self._max_visibles:
            self._mostrar(dto)
            return
        self._queue.append(dto)

    def _mostrar(self, dto: ToastDTO) -> None:
        if self._overlay is None:
            return
        widget = ToastWidget(dto, parent=self._overlay)
        widget.cerrado.connect(self._cerrar_toast)
        widget.solicitar_detalles.connect(self._abrir_detalles)
        self._overlay.layout_toasts.addWidget(widget, 0, Qt.AlignmentFlag.AlignHCenter)
        self._overlay.show()
        widget.show()
        self._visibles[dto.id] = widget

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda toast_id=dto.id: self._cerrar_toast(toast_id))
        timer.start(max(0, int(dto.duracion_ms or 8000)))
        self._timers[dto.id] = timer

    def _cerrar_toast(self, toast_id: str) -> None:
        timer = self._timers.pop(toast_id, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
        widget = self._visibles.pop(toast_id, None)
        if widget is not None:
            widget.hide()
            widget.deleteLater()
        if self._queue:
            self._mostrar(self._queue.popleft())
        elif self._overlay is not None and not self._visibles:
            self._overlay.hide()

    def _abrir_detalles(self, toast_id: str) -> None:
        dto = self._cache.get(toast_id)
        if dto is None or self._host is None:
            return
        dialog = DialogoDetallesToast(dto, parent=self._host)
        dialog.exec()

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
