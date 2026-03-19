from __future__ import annotations

from collections.abc import Callable
import traceback
from typing import Any
from uuid import uuid4

from app.ui.copy_catalog import copy_text

_REASON_CODE_SLOT_EXCEPTION = "QT_SLOT_EXCEPTION"


def _abrir_dialogo_detalle_error_default(
    *,
    titulo: str,
    resumen: str,
    detalle: str,
    incident_id: str | None,
) -> None:
    from app.ui.dialogos.dialogo_detalle_error import DialogoDetalleError

    dialogo = DialogoDetalleError(
        titulo=titulo,
        resumen=resumen,
        detalle=detalle,
        incident_id=incident_id,
    )
    ejecutar_modal = getattr(dialogo, "exec", None)
    if callable(ejecutar_modal):
        ejecutar_modal()
        return
    dialogo.show()


def _crear_callback_detalles_error(
    *,
    titulo: str,
    resumen: str,
    detalle: str,
    incident_id: str,
    logger: Any,
    dialog_factory: Callable[..., Any] | None,
) -> Callable[[], None]:
    resolved_factory = dialog_factory or _abrir_dialogo_detalle_error_default

    def _callback() -> None:
        try:
            resolved_factory(
                titulo=titulo,
                resumen=resumen,
                detalle=detalle,
                incident_id=incident_id,
            )
        except Exception:
            logger.exception(
                "qt_slot_error_details_dialog_exception",
                extra={
                    "reason_code": _REASON_CODE_SLOT_EXCEPTION,
                    "incident_id": incident_id,
                },
            )

    return _callback


def _notificar_error_toast(
    toast: Any,
    *,
    contexto: str,
    resumen: str,
    detalle: str,
    incident_id: str,
    logger: Any,
    dialog_factory: Callable[..., Any] | None,
) -> None:
    metodo_error = getattr(toast, "error", None)
    if not callable(metodo_error):
        return
    metodo_error(
        resumen,
        title=copy_text("ui.error_details.toast_title"),
        action_label=copy_text("ui.error_details.view_details"),
        action_callback=_crear_callback_detalles_error(
            titulo=copy_text("ui.error_details.title"),
            resumen=resumen,
            detalle=detalle,
            incident_id=incident_id,
            logger=logger,
            dialog_factory=dialog_factory,
        ),
        correlation_id=incident_id,
    )


def envolver_slot_seguro(
    fn: Callable[..., Any],
    *,
    contexto: str,
    logger: Any,
    toast: Any = None,
    dialog_factory: Callable[..., Any] | None = None,
) -> Callable[..., None]:
    def _slot_seguro(*args: Any, **kwargs: Any) -> None:
        try:
            fn(*args, **kwargs)
        except Exception:
            incident_id = str(uuid4())
            resumen = copy_text("ui.wiring.slot_error")
            detalle = traceback.format_exc()
            logger.exception(
                "qt_slot_exception",
                extra={
                    "reason_code": _REASON_CODE_SLOT_EXCEPTION,
                    "contexto": contexto,
                    "handler_name": getattr(fn, "__name__", repr(fn)),
                    "incident_id": incident_id,
                },
            )
            if toast is not None:
                try:
                    _notificar_error_toast(
                        toast,
                        contexto=contexto,
                        resumen=resumen,
                        detalle=detalle,
                        incident_id=incident_id,
                        logger=logger,
                        dialog_factory=dialog_factory,
                    )
                except Exception:
                    logger.exception(
                        "qt_slot_toast_exception",
                        extra={
                            "reason_code": _REASON_CODE_SLOT_EXCEPTION,
                            "contexto": contexto,
                            "handler_name": getattr(fn, "__name__", repr(fn)),
                            "incident_id": incident_id,
                        },
                    )

    return _slot_seguro
