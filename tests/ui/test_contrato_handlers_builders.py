from __future__ import annotations

import ast
from pathlib import Path


BUILDERS = (
    "app/ui/vistas/builders/builders_formulario_solicitud.py",
    "app/ui/vistas/builders/builders_tablas.py",
    "app/ui/vistas/builders/builders_sync_panel.py",
    "app/ui/vistas/builders/builders_barra_superior.py",
)
STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")
HANDLER_PREFIXES = (
    "_on_",
    "_apply_",
    "_update_",
    "_run_",
    "_refresh_",
    "_show_",
    "_bind_",
    "_schedule_",
    "_collect_",
    "_mark_",
)


def _is_window_attribute(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "window"


def _looks_like_handler(name: str) -> bool:
    return name.startswith(HANDLER_PREFIXES)


def _is_window_private_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and _is_window_attribute(node.func)
        and node.func.attr.startswith("_")
    )


def _extract_window_handlers_from_ast(tree: ast.AST) -> set[str]:
    handlers: set[str] = set()
    for node in ast.walk(tree):
        if _is_window_private_call(node):
            handlers.add(node.func.attr)
            continue
        if not _is_window_attribute(node):
            continue
        if not node.attr.startswith("_"):
            continue
        if not _looks_like_handler(node.attr):
            continue
        handlers.add(node.attr)
    return handlers


def test_builders_solo_referencian_handlers_existentes_en_main_window() -> None:
    codigo_main_window = STATE_CONTROLLER.read_text(encoding="utf-8")
    handlers_referenciados: set[str] = set()

    for builder in BUILDERS:
        codigo_builder = Path(builder).read_text(encoding="utf-8")
        ast_builder = ast.parse(codigo_builder, filename=builder)
        handlers_referenciados.update(_extract_window_handlers_from_ast(ast_builder))

    faltantes = [
        handler
        for handler in sorted(handlers_referenciados)
        if f"def {handler}(" not in codigo_main_window
    ]

    assert not faltantes, "\n".join(
        f"Falta handler requerido por builders_sync_panel.py: {handler}" for handler in faltantes
    )
