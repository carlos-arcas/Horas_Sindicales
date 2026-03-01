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
        for child in ast.walk(node):
            if _is_window_handler_attr(child):
                handlers.add(child.attr)
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


def test_extractor_detecta_llamadas_y_callbacks_status_to_label() -> None:
    tree = ast.parse(
        """
window._status_to_label("IDLE")
button.clicked.connect(window._status_to_label)
"""
    )

    handlers = _extract_window_handlers_from_ast(tree)

    assert "_status_to_label" in handlers
