from __future__ import annotations

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

    mensaje = "Operacion UI ejecutada fuera del hilo principal."
    extra = {"contexto": contexto, "reason_code": "UI_THREAD_ASSERT"}
    if _modo_ci_estricto():
        raise AssertionError(f"{mensaje} contexto={contexto}")
    logger.error(mensaje, extra=extra)
