from __future__ import annotations

import logging
import os
from collections.abc import Callable
from logging import Logger

from app.ui.qt_compat import QApplication, QThread, QTimer


def _modo_ci_estricto() -> bool:
    return os.getenv("CI", "").strip().lower() in {"1", "true", "yes", "on"}


def es_hilo_ui() -> bool:
    app = QApplication.instance() if hasattr(QApplication, "instance") else None
    if app is None:
        return False
    app_thread_getter = getattr(app, "thread", None)
    if not callable(app_thread_getter):
        return False
    if not hasattr(QThread, "currentThread"):
        return False
    return QThread.currentThread() is app_thread_getter()


def comparar_threads(hilo_actual: object, hilo_ui: object) -> bool:
    return hilo_actual is hilo_ui


def derivar_nombre_operacion(operacion: object | None) -> str | None:
    if operacion is None:
        return None
    nombre = getattr(operacion, "__qualname__", None)
    if isinstance(nombre, str) and nombre:
        return nombre
    return None


def asegurar_en_hilo_ui(operacion: object | None = None) -> None:
    logger = logging.getLogger(__name__)
    app = QApplication.instance() if hasattr(QApplication, "instance") else None
    hilo_ui = app.thread() if app is not None and hasattr(app, "thread") else None
    hilo_actual = QThread.currentThread() if hasattr(QThread, "currentThread") else None
    nombre_operacion = derivar_nombre_operacion(operacion)

    if hilo_ui is not None and comparar_threads(hilo_actual, hilo_ui):
        return

    logger.error(
        "UI_QT_THREAD_VIOLATION",
        extra={
            "extra": {
                "operacion": nombre_operacion,
                "hilo_actual": repr(hilo_actual),
                "hilo_ui": repr(hilo_ui),
            }
        },
    )
    raise RuntimeError()


def ejecutar_en_hilo_ui(
    fn: Callable[[], None],
    *,
    contexto: str,
    logger: Logger,
    correlation_id: str | None = None,
) -> None:
    if es_hilo_ui():
        fn()
        return

    logger.info(
        "Dispatch de accion al hilo UI.",
        extra={
            "contexto": contexto,
            "reason_code": "UI_THREAD_DISPATCH",
            "correlation_id": correlation_id,
        },
    )
    if hasattr(QTimer, "singleShot"):
        QTimer.singleShot(0, fn)
        return
    fn()


def assert_hilo_ui_o_log(contexto: str, logger: Logger) -> None:
    if es_hilo_ui():
        return

    extra = {"contexto": contexto, "reason_code": "UI_THREAD_ASSERT"}
    if _modo_ci_estricto():
        raise AssertionError(contexto)
    logger.error("UI_THREAD_ASSERT", extra=extra)


def obtener_ids_hilos_qt() -> dict[str, str]:
    app = QApplication.instance() if hasattr(QApplication, "instance") else None
    hilo_actual = QThread.currentThread() if hasattr(QThread, "currentThread") else None
    hilo_ui = app.thread() if app is not None and hasattr(app, "thread") else None
    return {
        "hilo_actual_repr": repr(hilo_actual),
        "hilo_ui_repr": repr(hilo_ui),
    }


def detener_y_destruir_timer_seguro(
    timer,
    *,
    nombre: str,
    logger: Logger,
    marcar_stage: Callable[[str], None],
) -> None:
    if timer is None:
        return

    try:
        import shiboken6

        if not shiboken6.isValid(timer):
            logger.warning(
                "timer_invalido_ignorado",
                extra={"extra": {"nombre": nombre}},
            )
            return
    except Exception:
        pass

    try:
        timer.stop()
        marcar_stage("watchdog_stopped")
    except RuntimeError:
        logger.warning(
            "timer_stop_runtime_error_ignorado",
            extra={"extra": {"nombre": nombre}},
        )

    try:
        timer.deleteLater()
    except RuntimeError:
        logger.warning(
            "timer_delete_runtime_error_ignorado",
            extra={"extra": {"nombre": nombre}},
        )
