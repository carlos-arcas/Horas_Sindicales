from __future__ import annotations

from typing import Callable

from app.ui.widgets.dialogo_detalles_toast import DialogoDetallesNotificacion
from app.ui.widgets.gestor_toasts import GestorToasts as _GestorToastsBase
from app.ui.widgets.overlay_toast import CapaToasts
from app.ui.widgets.widget_toast import NotificacionToast, TarjetaToast


class GestorToasts(_GestorToastsBase):
    def success(
        self,
        message: str,
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
        self.show(
            message=message,
            level="success",
            title=title,
            action_label=action_label,
            action_callback=action_callback,
            details=details,
            correlation_id=correlation_id,
            code=code,
            duration_ms=duration_ms,
            **opts,
        )

    def info(
        self,
        message: str,
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
        self.show(
            message=message,
            level="info",
            title=title,
            action_label=action_label,
            action_callback=action_callback,
            details=details,
            correlation_id=correlation_id,
            code=code,
            duration_ms=duration_ms,
            **opts,
        )

    def warning(
        self,
        message: str,
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
        self.show(
            message=message,
            level="warning",
            title=title,
            action_label=action_label,
            action_callback=action_callback,
            details=details,
            correlation_id=correlation_id,
            code=code,
            duration_ms=duration_ms,
            **opts,
        )

    def error(
        self,
        message: str,
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
        payload_details = details if isinstance(details, str) else opts.get("details") if isinstance(opts.get("details"), str) else None
        payload_message = f"{message}\n{payload_details}" if payload_details else message
        self.show(
            message=payload_message,
            level="error",
            title=title,
            action_label=action_label,
            action_callback=action_callback,
            details=payload_details,
            correlation_id=correlation_id,
            code=code,
            duration_ms=duration_ms,
            **opts,
        )


class ToastManager(GestorToasts):
    """Alias retrocompatible del facade de toasts.

    Mantiene la firma pública histórica (`success/error` con
    `action_label/action_callback`) delegando íntegramente en `GestorToasts`.
    """


Toast = TarjetaToast


def _on_action_clicked() -> None:
    return None


# action_button.clicked.connect(self._on_action_clicked)
__all__ = [
    Toast.__name__,
    NotificacionToast.__name__,
    GestorToasts.__name__,
    ToastManager.__name__,
    TarjetaToast.__name__,
    CapaToasts.__name__,
    DialogoDetallesNotificacion.__name__,
]
