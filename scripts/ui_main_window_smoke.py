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
    "_on_completo_changed",
    "_on_add_pendiente",
    "_on_confirmar",
    "_update_solicitud_preview",
    "_apply_historico_default_range",
    "_status_to_label",
    "_normalize_input_heights",
    "_update_responsive_columns",
    "_configure_time_placeholders",
    "_configure_operativa_focus_order",
    "_configure_historico_focus_order",
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
QT_THREAD_PARENT_WARNING = (
    "Cannot create children for a parent that is in a different thread"
)


def _extraer_metodos_clase_ast(path: Path, class_name: str) -> set[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                item.name for item in node.body if isinstance(item, ast.FunctionDef)
            }
    return set()


def _validar_handlers_por_ast() -> int:
    vista_methods = _extraer_metodos_clase_ast(
        ROOT / "app" / "ui" / "vistas" / "main_window_vista.py", "MainWindow"
    )
    base_methods = _extraer_metodos_clase_ast(
        ROOT / "app" / "ui" / "vistas" / "main_window" / "state_controller.py",
        "MainWindow",
    )
    method_names = vista_methods | base_methods
    if not method_names:
        logger.error("main_window_class_missing_ast")
        return 1
    missing = [name for name in REQUIRED_HANDLERS if name not in method_names]
    if missing:
        logger.error("missing_handlers_ast: %s", ", ".join(missing))
        return 1
    logger.info("ui_main_window_smoke_ok_ast")
    return 0


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
    return (
        f"SMOKE_UI_FAIL: {type(exc).__name__} {exc} "
        f"archivo:linea {file_name}:{last_frame.lineno}"
    )


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
        qt_core = importlib.import_module("PySide6.QtCore")
        app = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
        qt_messages: list[str] = []

        def _qt_message_handler(_msg_type, _context, message) -> None:
            if QT_THREAD_PARENT_WARNING in message:
                qt_messages.append(message)

        previous_handler = qt_core.qInstallMessageHandler(_qt_message_handler)
        module = importlib.import_module("app.ui.main_window")
        main_window_cls = getattr(module, "MainWindow", None)
        if main_window_cls is None:
            raise AttributeError("MainWindow no esta definido en app.ui.main_window")
        header_state_module = importlib.import_module(
            "app.ui.vistas.main_window.header_state"
        )
        resolve_section_title = header_state_module.resolve_section_title

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
            estado_modo_solo_lectura=container.estado_modo_solo_lectura,
        )
        app.processEvents()

        # Valida que el shell mantiene sincronizados tab activo y header externo.
        titles_seen: set[str] = set()
        for sidebar_index in (0, 1, 2, 3, 1):
            window._switch_sidebar_page(sidebar_index)
            app.processEvents()
            header_title = getattr(window, "header_title_label", None)
            active_sidebar_index = getattr(window, "_active_sidebar_index", None)
            expected_title = resolve_section_title(active_sidebar_index)
            if header_title is None or header_title.text() != expected_title:
                raise AssertionError(
                    "El header externo no quedo sincronizado con la seccion activa tras navegar"
                )
            titles_seen.add(header_title.text())
        if len(titles_seen) < 3:
            raise AssertionError(
                "El header externo no recorrio suficientes titulos durante el smoke"
            )

        if window.findChild(qt_widgets.QWidget, "header_shell") is not None:
            raise AssertionError("Se detecto header_shell global no permitido")
        if qt_messages:
            raise AssertionError(
                "Se detecto warning Qt de parent en hilo distinto: "
                + " | ".join(qt_messages)
            )
    except Exception as exc:  # pragma: no cover - fallo defensivo
        if "libGL.so.1" in str(exc):
            logger.warning("ui_import_fallback_ast: %s", exc)
            return _validar_handlers_por_ast()
        log_operational_error(
            logger,
            "ui_main_window_smoke_failed",
            exc=sys.exc_info(),
            extra={
                "script": "ui_main_window_smoke.py",
                "error_type": type(exc).__name__,
            },
        )
        if _should_fail_gate(exc):
            logger.error(_format_exception_summary(exc))
            return 1
        logger.warning("SMOKE_UI_WARN: %s %s", type(exc).__name__, exc)
        return 0
    finally:
        if "qt_core" in locals() and "previous_handler" in locals():
            qt_core.qInstallMessageHandler(previous_handler)

    missing = [
        name for name in REQUIRED_HANDLERS if not callable(getattr(type(window), name, None))
    ]
    if missing:
        message = f"Missing handlers: {', '.join(missing)}"
        log_operational_error(
            logger,
            "ui_main_window_smoke_missing_handlers",
            exc=AttributeError(message),
        )
        logger.error(
            "SMOKE_UI_FAIL: AttributeError %s archivo:linea ui_main_window_smoke.py:0",
            message,
        )
        window.close()
        app.processEvents()
        return 1

    window.close()
    app.processEvents()

    logger.info("ui_main_window_smoke_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
