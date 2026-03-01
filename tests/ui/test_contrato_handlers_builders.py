from __future__ import annotations

import ast
from pathlib import Path


BUILDERS = (
    "app/ui/vistas/builders/main_window_builders.py",
    "app/ui/vistas/builders/builders_formulario_solicitud.py",
    "app/ui/vistas/builders/builders_tablas.py",
    "app/ui/vistas/builders/builders_sync_panel.py",
)


def _is_window_handler_attr(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "window"
        and node.attr.startswith("_")
    )


def _extract_window_handlers_from_ast(tree: ast.AST) -> set[str]:
    handlers: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_window_handler_attr(node.func):
            handlers.add(node.func.attr)
        for arg in node.args:
            if _is_window_handler_attr(arg):
                handlers.add(arg.attr)
        for keyword in node.keywords:
            if _is_window_handler_attr(keyword.value):
                handlers.add(keyword.value.attr)
    return handlers


def _missing_handlers_for_builder(builder: str, main_window_cls: type) -> list[str]:
    code = Path(builder).read_text(encoding="utf-8")
    tree = ast.parse(code, filename=builder)
    handlers = _extract_window_handlers_from_ast(tree)
    return sorted(
        handler
        for handler in handlers
        if not hasattr(main_window_cls, handler) or not callable(getattr(main_window_cls, handler, None))
    )


def test_builders_referencian_handlers_presentes_y_callables_en_main_window() -> None:
    from app.ui.vistas.main_window.state_controller import MainWindow

    missing_messages: list[str] = []
    for builder in BUILDERS:
        missing_handlers = _missing_handlers_for_builder(builder, MainWindow)
        missing_messages.extend(
            f"Falta handler requerido por {Path(builder).name}: {handler}"
            for handler in missing_handlers
        )

    assert not missing_messages, "\n".join(missing_messages)
