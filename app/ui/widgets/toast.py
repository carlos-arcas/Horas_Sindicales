from __future__ import annotations

import logging
from typing import Callable

from app.ui.toasts.accion_toast import AccionToast
from app.ui.widgets.dialogo_detalles_toast import DialogoDetallesNotificacion
from app.ui.widgets.gestor_toasts import GestorToasts as _GestorToastsBase
from app.ui.widgets.overlay_toast import CapaToasts
from app.ui.widgets.widget_toast import NotificacionToast, TarjetaToast

logger = logging.getLogger(__name__)


class GestorToasts(_GestorToastsBase):
    def _show_tolerante(self, **kwargs: object) -> None:
        try:
            self.show(**kwargs)
        except TypeError:
            action_label = kwargs.get("action_label")
            if action_label is not None:
                logger.warning(
                    "TOAST_ACTION_NOT_SUPPORTED",
                    extra={"action_label": action_label},
                )
            kwargs_filtrados = {
                clave: kwargs.get(clave)
                for clave in (
                    "message",
                    "level",
                    "title",
                    "details",
                    "correlation_id",
                    "code",
                    "origin",
                    "exc_info",
                    "duration_ms",
                )
            }
            self.show(**kwargs_filtrados)

    def _resolver_aliases_accion(
        self,
        *,
        action_label: str | None,
        action_callback: Callable[[], None] | None,
        opts: dict[str, object],
    ) -> AccionToast:
        claves_permitidas = {"action_text", "action"}
        claves_desconocidas = sorted(set(opts.keys()) - claves_permitidas)
        if claves_desconocidas:
            logger.error(
                "toast_kwargs_invalidos",
                extra={"kwargs_no_soportados": claves_desconocidas},
            )
            raise ValueError(f"toast_kwargs_invalidos:{','.join(claves_desconocidas)}")

        if (action_label is None) != (action_callback is None):
            logger.warning(
                "TOAST_ACTION_INCOMPLETE",
                extra={
                    "action_label": action_label,
                    "has_action_callback": action_callback is not None,
                },
            )
            action_label = None
            action_callback = None

        return AccionToast.desde_argumentos(
            action_label=action_label,
            action_callback=action_callback,
            action_text=opts.get("action_text"),
            action=opts.get("action"),
        )

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
        accion = self._resolver_aliases_accion(
            action_label=action_label,
            action_callback=action_callback,
            opts=opts,
        )

        self._show_tolerante(
            message=message,
            level="success",
            title=title,
            action_label=accion.etiqueta,
            action_callback=accion.callback,
            details=details,
            correlation_id=correlation_id,
            code=code,
            duration_ms=duration_ms,
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
        accion = self._resolver_aliases_accion(
            action_label=action_label,
            action_callback=action_callback,
            opts=opts,
        )

        self._show_tolerante(
            message=message,
            level="info",
            title=title,
            action_label=accion.etiqueta,
            action_callback=accion.callback,
            details=details,
            correlation_id=correlation_id,
            code=code,
            duration_ms=duration_ms,
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
        accion = self._resolver_aliases_accion(
            action_label=action_label,
            action_callback=action_callback,
            opts=opts,
        )

        self._show_tolerante(
            message=message,
            level="warning",
            title=title,
            action_label=accion.etiqueta,
            action_callback=accion.callback,
            details=details,
            correlation_id=correlation_id,
            code=code,
            duration_ms=duration_ms,
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
        accion = self._resolver_aliases_accion(
            action_label=action_label,
            action_callback=action_callback,
            opts=opts,
        )
        self._show_tolerante(
            message=message,
            level="error",
            title=title,
            action_label=accion.etiqueta,
            action_callback=accion.callback,
            details=details,
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

    def success(
        self,
        mensaje: str,
        *,
        title: str | None = None,
        action_label: str | None = None,
        action_callback: Callable[[], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().success(
            mensaje,
            title=title,
            action_label=action_label,
            action_callback=action_callback,
            **kwargs,
        )

    def error(
        self,
        mensaje: str,
        *,
        title: str | None = None,
        action_label: str | None = None,
        action_callback: Callable[[], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().error(
            mensaje,
            title=title,
            action_label=action_label,
            action_callback=action_callback,
            **kwargs,
        )


Toast = TarjetaToast


__all__ = [
    Toast.__name__,
    NotificacionToast.__name__,
    GestorToasts.__name__,
    ToastManager.__name__,
    TarjetaToast.__name__,
    CapaToasts.__name__,
    DialogoDetallesNotificacion.__name__,
]
