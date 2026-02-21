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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Evita abrir UI visible en entornos CI/headless.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

logging.basicConfig(level=logging.INFO, format="%(levelname)s event=%(message)s")
logger = logging.getLogger(__name__)

REQUIRED_HANDLERS = (
    "_sincronizar_con_confirmacion",
    "_on_sync_with_confirmation",
    "_limpiar_formulario",
    "_clear_form",
    "_verificar_handlers_ui",
    "eventFilter",
)

GATE_FAIL_EXCEPTIONS = (NameError, AttributeError, ImportError, TypeError)


def log_operational_error(event: str, exc_info: BaseException) -> None:
    summary = _format_short_exception(exc_info).replace("SMOKE_UI_FAIL: ", "")
    logger.error("error_operativo event=%s exc_info=%s", event, summary)


def _format_short_exception(exc: BaseException) -> str:
    tb = traceback.extract_tb(exc.__traceback__)
    if tb:
        last = tb[-1]
        return f"SMOKE_UI_FAIL: {type(exc).__name__} {exc} {last.filename}:{last.lineno}"
    return f"SMOKE_UI_FAIL: {type(exc).__name__} {exc}"


def _print_fail_summary(exc: BaseException) -> None:
    print(_format_short_exception(exc), file=sys.stdout)


def _validar_handlers_por_ast() -> list[str]:
    source = (ROOT / "app" / "ui" / "vistas" / "main_window_vista.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow":
            method_names = {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
            return [name for name in REQUIRED_HANDLERS if name not in method_names]
    return ["MainWindow"]


def _ensure_qapplication() -> object | None:
    try:
        widgets = importlib.import_module("PySide6.QtWidgets")
    except Exception:
        return None
    app = widgets.QApplication.instance()
    if app is None:
        app = widgets.QApplication([])
    return app


def main() -> int:
    _ensure_qapplication()
    try:
        module = importlib.import_module("app.ui.vistas.main_window_vista")
    except GATE_FAIL_EXCEPTIONS as exc:
        if isinstance(exc, ImportError) and "libGL.so.1" in str(exc):
            logger.warning("ui_import_fallback_ast: %s", exc)
            missing_ast = _validar_handlers_por_ast()
            if missing_ast:
                missing_exc = AttributeError(f"missing_handlers_ast: {', '.join(missing_ast)}")
                log_operational_error("precheck_ui_ast", missing_exc)
                _print_fail_summary(missing_exc)
                return 1
            logger.info("ui_main_window_smoke_ok_ast")
            return 0
        log_operational_error("precheck_ui_import", exc)
        _print_fail_summary(exc)
        return 1
    except Exception as exc:  # pragma: no cover - fallo defensivo
        log_operational_error("precheck_ui_import_unexpected", exc)
        _print_fail_summary(exc)
        return 1

    main_window_cls = getattr(module, "MainWindow", None)
    if main_window_cls is None:
        exc = AttributeError("MainWindow class missing")
        log_operational_error("precheck_ui_mainwindow_missing", exc)
        _print_fail_summary(exc)
        return 1

    missing = [name for name in REQUIRED_HANDLERS if not callable(getattr(main_window_cls, name, None))]
    if missing:
        exc = AttributeError(f"missing_handlers: {', '.join(missing)}")
        log_operational_error("precheck_ui_handlers", exc)
        _print_fail_summary(exc)
        return 1

    logger.info("ui_main_window_smoke_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
