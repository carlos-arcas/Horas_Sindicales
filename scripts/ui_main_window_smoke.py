#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


def main() -> int:
    try:
        module = importlib.import_module("app.ui.vistas.main_window_vista")
    except Exception as exc:  # pragma: no cover - fallo defensivo
        if "libGL.so.1" in str(exc):
            logger.warning("ui_import_fallback_ast: %s", exc)
            return _validar_handlers_por_ast()
        logger.exception("ui_import_failed: %s", exc)
        return 1

    main_window_cls = getattr(module, "MainWindow", None)
    if main_window_cls is None:
        logger.error("main_window_class_missing")
        return 1

    missing = [name for name in REQUIRED_HANDLERS if not callable(getattr(main_window_cls, name, None))]
    if missing:
        logger.error("missing_handlers: %s", ", ".join(missing))
        return 1

    logger.info("ui_main_window_smoke_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
