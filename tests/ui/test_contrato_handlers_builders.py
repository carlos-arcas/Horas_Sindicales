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


def test_builders_referencian_handlers_presentes_y_callables_en_main_window() -> None:
    handlers_referenciados: set[str] = set()

    for builder in BUILDERS:
        codigo_builder = Path(builder).read_text(encoding="utf-8")
        ast_builder = ast.parse(codigo_builder, filename=builder)
        handlers_referenciados.update(_extract_window_handlers_from_ast(ast_builder))

    from app.ui.vistas.main_window.state_controller import MainWindow

    faltantes = sorted(
        handler
        for handler in handlers_referenciados
        if not hasattr(MainWindow, handler) or not callable(getattr(MainWindow, handler, None))
    )

    assert not faltantes, (
        "Handlers faltantes/no callables en MainWindow detectados desde builders "
        f"(calls/callbacks): {', '.join(faltantes)}"
    )
