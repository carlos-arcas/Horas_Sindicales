#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib
import logging
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)

REQUIRED_HANDLERS = (
    "_sincronizar_con_confirmacion",
    "_on_sync_with_confirmation",
    "_limpiar_formulario",
    "_clear_form",
    "_verificar_handlers_ui",
    "eventFilter",
)

FAIL_GATE_EXCEPTIONS = (NameError, AttributeError, ImportError)
BENIGN_QT_WARNING_HINTS = (
    "QStandardPaths: XDG_RUNTIME_DIR not set",
    "This plugin does not support propagateSizeHints",
)
WIRING_TYPE_ERROR_HINTS = (
    "connect",
    "signal",
    "slot",
    "positional argument",
    "unexpected keyword",
)


def _validar_handlers_por_ast() -> int:
    source = (ROOT / "app" / "ui" / "vistas" / "main_window_vista.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow":
            method_names = {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
            missing = [name for name in REQUIRED_HANDLERS if name not in method_names]
            if missing:
                logger.error("missing_handlers_ast: %s", ", ".join(missing))
                return 1
            logger.info("ui_main_window_smoke_ok_ast")
            return 0
    logger.error("main_window_class_missing_ast")
    return 1


def _in_memory_connection():
    import sqlite3

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def _format_exception_summary(exc: BaseException) -> str:
    last_frame = traceback.extract_tb(exc.__traceback__)[-1] if exc.__traceback__ else None
    if last_frame is None:
        return f"SMOKE_UI_FAIL: {type(exc).__name__} {exc} archivo:linea N/D"
    file_name = Path(last_frame.filename).name
    return f"SMOKE_UI_FAIL: {type(exc).__name__} {exc} archivo:linea {file_name}:{last_frame.lineno}"


def _is_wiring_type_error(exc: BaseException) -> bool:
    if not isinstance(exc, TypeError):
        return False
    message = str(exc).lower()
    return any(hint in message for hint in WIRING_TYPE_ERROR_HINTS)


def _is_benign_qt_warning(exc: BaseException) -> bool:
    message = str(exc)
    return any(hint in message for hint in BENIGN_QT_WARNING_HINTS)


def _should_fail_gate(exc: BaseException) -> bool:
    if _is_benign_qt_warning(exc):
        return False
    if isinstance(exc, FAIL_GATE_EXCEPTIONS):
        return True
    if _is_wiring_type_error(exc):
        return True
    return True


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from app.bootstrap.container import build_container
    from app.bootstrap.logging import configure_logging, log_operational_error

    configure_logging(ROOT / "logs", level=logging.INFO)

    try:
        qt_widgets = importlib.import_module("PySide6.QtWidgets")
        app = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
        module = importlib.import_module("app.ui.main_window")
        main_window_cls = getattr(module, "MainWindow", None)
        if main_window_cls is None:
            raise AttributeError("MainWindow no está definido en app.ui.main_window")

        container = build_container(connection_factory=_in_memory_connection)
        window = main_window_cls(
            container.persona_use_cases,
            container.solicitud_use_cases,
            container.grupo_use_cases,
            container.sheets_service,
            container.sync_service,
            container.conflicts_service,
            health_check_use_case=None,
            alert_engine=container.alert_engine,
        )
        app.processEvents()

        # Smoke de navegación entre secciones para validar que el shell externo
        # actualiza el header dinámico sin errores de señales/layout.
        for sidebar_index in (0, 1, 2, 3, 1):
            window._switch_sidebar_page(sidebar_index)
            app.processEvents()

        expected_title = "Solicitudes"
        header_title = getattr(window, "header_title_label", None)
        if header_title is None or header_title.text() != expected_title:
            raise AssertionError("El header externo no actualizó el título esperado tras navegar secciones")

        # Guard-rail: el contenido no debe volver a montar un HeaderWidget interno.
        header_module = importlib.import_module("app.ui.widgets.header")
        header_widget_cls = getattr(header_module, "HeaderWidget")
        content_page = getattr(window, "page_solicitudes", None)
        search_root = content_page if content_page is not None else window
        internal_headers = search_root.findChildren(header_widget_cls)
        if internal_headers:
            raise AssertionError("Se detectó HeaderWidget interno en la zona de contenido")
    except Exception as exc:  # pragma: no cover - fallo defensivo
        if "libGL.so.1" in str(exc):
            logger.warning("ui_import_fallback_ast: %s", exc)
            return _validar_handlers_por_ast()
        log_operational_error(
            logger,
            "ui_main_window_smoke_failed",
            exc=sys.exc_info(),
            extra={"script": "ui_main_window_smoke.py", "error_type": type(exc).__name__},
        )
        if _should_fail_gate(exc):
            logger.error(_format_exception_summary(exc))
            return 1
        logger.warning("SMOKE_UI_WARN: %s %s", type(exc).__name__, exc)
        return 0

    missing = [name for name in REQUIRED_HANDLERS if not callable(getattr(type(window), name, None))]
    if missing:
        message = f"Missing handlers: {', '.join(missing)}"
        log_operational_error(logger, "ui_main_window_smoke_missing_handlers", exc=AttributeError(message))
        logger.error("SMOKE_UI_FAIL: AttributeError %s archivo:linea ui_main_window_smoke.py:0", message)
        window.close()
        app.processEvents()
        return 1

    window.close()
    app.processEvents()

    logger.info("ui_main_window_smoke_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
