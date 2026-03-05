from __future__ import annotations

import logging
import os
from typing import Any, Callable
import traceback
MENSAJE_VIOLACION_THREAD_PARENT = "Cannot create children for a parent that is in a different thread"


class BootTraceWriterProtocol:
    def marcar_stage(self, stage: str) -> None:  # pragma: no cover - protocolo informal
        raise NotImplementedError


class QtMessageHandlerState:
    def __init__(self) -> None:
        self.violacion_thread_parent_detectada = False


_QT_MESSAGE_HANDLER_STATE = QtMessageHandlerState()


def _normalizar_tipo_mensaje(tipo: Any) -> str:
    tipo_nombre = getattr(tipo, "name", "")
    if tipo_nombre:
        return str(tipo_nombre)
    return str(tipo)


def _serializar_contexto(contexto: Any) -> dict[str, Any]:
    return {
        "categoria": str(getattr(contexto, "category", "") or ""),
        "archivo": str(getattr(contexto, "file", "") or ""),
        "linea": int(getattr(contexto, "line", 0) or 0),
        "funcion": str(getattr(contexto, "function", "") or ""),
    }


def _es_violacion_thread_parent(mensaje: str) -> bool:
    return MENSAJE_VIOLACION_THREAD_PARENT in mensaje


def _registrar_stage_violacion(boot_trace_writer: BootTraceWriterProtocol | None) -> None:
    if boot_trace_writer is None:
        return
    marcar_stage = getattr(boot_trace_writer, "marcar_stage", None)
    if callable(marcar_stage):
        marcar_stage("QT_THREAD_PARENT_VIOLATION")


def _debe_fallar_ci() -> bool:
    return os.getenv("CI", "").strip().lower() in {"1", "true", "yes", "on"}


def _levantar_assertion_en_hilo_ui() -> None:
    from PySide6.QtCore import QTimer

    def _raise_assertion() -> None:
        raise AssertionError(MENSAJE_VIOLACION_THREAD_PARENT)

    QTimer.singleShot(0, _raise_assertion)


def _resolver_nivel_log(tipo_qt: Any, violacion_thread_parent: bool) -> int:
    if violacion_thread_parent:
        return logging.ERROR
    tipo_nombre = _normalizar_tipo_mensaje(tipo_qt).lower()
    if "critical" in tipo_nombre or "fatal" in tipo_nombre:
        return logging.ERROR
    if "warning" in tipo_nombre:
        return logging.WARNING
    if "debug" in tipo_nombre:
        return logging.DEBUG
    return logging.INFO


def construir_payload_qt(
    *,
    tipo_qt: Any,
    contexto: Any,
    mensaje: str,
    violacion_thread_parent: bool,
) -> dict[str, Any]:
    qt_payload: dict[str, Any] = {
        "tipo": _normalizar_tipo_mensaje(tipo_qt),
        **_serializar_contexto(contexto),
        "mensaje": mensaje,
        "thread_parent_violation": violacion_thread_parent,
    }
    if violacion_thread_parent:
        qt_payload["stacktrace_python"] = traceback.format_stack(limit=25)
    return {"qt": qt_payload}


def _procesar_mensaje_qt(
    *,
    tipo_qt: Any,
    contexto: Any,
    mensaje: str,
    logger: logging.Logger,
    boot_trace_writer: BootTraceWriterProtocol | None,
) -> None:
    violacion_thread_parent = _es_violacion_thread_parent(mensaje)
    if violacion_thread_parent:
        _QT_MESSAGE_HANDLER_STATE.violacion_thread_parent_detectada = True
        _registrar_stage_violacion(boot_trace_writer)

    extra = construir_payload_qt(
        tipo_qt=tipo_qt,
        contexto=contexto,
        mensaje=mensaje,
        violacion_thread_parent=violacion_thread_parent,
    )
    logger.log(
        _resolver_nivel_log(tipo_qt, violacion_thread_parent),
        "Qt message captured",
        extra={"extra": extra},
    )

    if violacion_thread_parent and _debe_fallar_ci():
        _levantar_assertion_en_hilo_ui()


def instalar_qt_message_handler(
    logger: logging.Logger,
    boot_trace_writer: BootTraceWriterProtocol | None,
) -> Callable[..., Any] | None:
    try:
        from PySide6.QtCore import qInstallMessageHandler
    except (ImportError, ModuleNotFoundError):
        logger.warning("PySide6 no disponible: se omite qInstallMessageHandler")
        return None

    def _handler(tipo_qt, contexto, mensaje) -> None:
        _procesar_mensaje_qt(
            tipo_qt=tipo_qt,
            contexto=contexto,
            mensaje=str(mensaje),
            logger=logger,
            boot_trace_writer=boot_trace_writer,
        )

    qInstallMessageHandler(_handler)
    return _handler
