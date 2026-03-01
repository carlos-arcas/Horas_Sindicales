from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


BUILDERS = (
    "app/ui/vistas/builders/main_window_builders.py",
    "app/ui/vistas/builders/builders_formulario_solicitud.py",
    "app/ui/vistas/builders/builders_tablas.py",
    "app/ui/vistas/builders/builders_sync_panel.py",
)
FUENTES_HANDLERS = (
    "app/ui/vistas/main_window/state_controller.py",
    "app/ui/vistas/main_window_vista.py",
)
PREFIJOS_HANDLER = (
    "_on_",
    "_apply_",
    "_update_",
    "_normalize_",
    "_refresh_",
    "_configure_",
    "_bind_",
    "_restore_",
    "_run_",
    "_focus_",
    "_sync_",
    "_build_",
    "_load_",
    "_save_",
)


@dataclass(frozen=True)
class HandlerRequirement:
    builder: str
    line: int
    handler: str
    patron: str
    contexto: str = "-"


def _is_handler_privado(nombre: str) -> bool:
    return nombre.startswith(PREFIJOS_HANDLER)


def _is_window_handler_attr(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "window"
        and _is_handler_privado(node.attr)
    )


def _is_conectar_signal_call(node: ast.Call) -> bool:
    if isinstance(node.func, ast.Name):
        return node.func.id == "conectar_signal"
    return isinstance(node.func, ast.Attribute) and node.func.attr == "conectar_signal"


def _extract_literal_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_handler_name_from_call(node: ast.Call) -> str | None:
    for kw in node.keywords:
        if kw.arg == "handler_name":
            return _extract_literal_str(kw.value)
    if len(node.args) >= 3:
        return _extract_literal_str(node.args[2])
    return None


def _extract_contexto_from_call(node: ast.Call) -> str:
    for kw in node.keywords:
        if kw.arg == "contexto":
            return _extract_literal_str(kw.value) or "<contexto-no-literal>"
    return "<sin-contexto>"


def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parent_map: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent
    return parent_map


def _extract_connect_window_handlers(tree: ast.AST, builder: str) -> list[HandlerRequirement]:
    requirements: list[HandlerRequirement] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "connect":
            continue
        for arg in node.args:
            if _is_window_handler_attr(arg):
                requirements.append(HandlerRequirement(builder, node.lineno, arg.attr, "connect(window._handler)"))
    return requirements


def _extract_direct_window_calls(tree: ast.AST, builder: str) -> list[HandlerRequirement]:
    requirements: list[HandlerRequirement] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_window_handler_attr(node.func):
            continue
        requirements.append(HandlerRequirement(builder, node.lineno, node.func.attr, "window._handler()"))
    return requirements


def _extract_window_attr_accesses(tree: ast.AST, builder: str) -> list[HandlerRequirement]:
    parent_map = _build_parent_map(tree)
    requirements: list[HandlerRequirement] = []
    for node in ast.walk(tree):
        if not _is_window_handler_attr(node):
            continue
        parent = parent_map.get(node)
        if isinstance(parent, ast.Call) and (parent.func is node or node in parent.args):
            continue
        requirements.append(HandlerRequirement(builder, node.lineno, node.attr, "window._handler (atributo)"))
    return requirements


def _extract_conectar_signal_handler_requirements(tree: ast.AST, builder: str) -> list[HandlerRequirement]:
    requirements: list[HandlerRequirement] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_conectar_signal_call(node):
            continue
        handler = _extract_handler_name_from_call(node)
        if handler is None or not _is_handler_privado(handler):
            continue
        requirements.append(
            HandlerRequirement(
                builder=builder,
                line=node.lineno,
                handler=handler,
                patron='conectar_signal(..., handler_name="...")',
                contexto=_extract_contexto_from_call(node),
            )
        )
    return requirements


def _extract_requirements_from_builder(tree: ast.AST, builder: str) -> list[HandlerRequirement]:
    requirements = _extract_connect_window_handlers(tree, builder)
    requirements.extend(_extract_direct_window_calls(tree, builder))
    requirements.extend(_extract_window_attr_accesses(tree, builder))
    requirements.extend(_extract_conectar_signal_handler_requirements(tree, builder))
    return requirements


def _read_ast(path: str) -> ast.AST:
    return ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)


def _extract_defined_functions_from_ast(tree: ast.AST) -> set[str]:
    defs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.add(node.name)
    return defs


def _collect_builder_trees() -> list[tuple[str, ast.AST]]:
    return [(builder, _read_ast(builder)) for builder in BUILDERS]


def _collect_defined_handlers() -> set[str]:
    handlers: set[str] = set()
    for source in FUENTES_HANDLERS:
        if Path(source).exists():
            handlers.update(_extract_defined_functions_from_ast(_read_ast(source)))
    return handlers


def _format_missing_requirements(missing: list[HandlerRequirement]) -> str:
    ordered = sorted(missing, key=lambda item: (item.builder, item.line, item.handler, item.patron))
    lines = [
        (
            f"- {item.builder}:{item.line} | handler={item.handler} | patron={item.patron}"
            f" | contexto={item.contexto}"
        )
        for item in ordered
    ]
    return (
        "Faltan handlers requeridos por builders. "
        "Revisa el handler o agrega binding/def en state_controller.py o main_window_vista.py.\n"
        + "\n".join(lines)
    )


def test_builders_referencian_handlers_presentes_en_fuentes_ast() -> None:
    handlers_definidos = _collect_defined_handlers()
    requirements: list[HandlerRequirement] = []

    for builder, tree in _collect_builder_trees():
        requirements.extend(_extract_requirements_from_builder(tree, builder))

    missing = [req for req in requirements if req.handler not in handlers_definidos]

    assert not missing, _format_missing_requirements(missing)


def test_extractor_detecta_patrones_requeridos() -> None:
    tree = ast.parse(
        """
window._normalize_input_heights()
button.clicked.connect(window._update_responsive_columns)
x = window._refresh_header_title
conectar_signal(window, signal, "_on_confirmar", contexto="confirmar")
conectar_signal(window, signal, handler_name="_apply_historico_filters", contexto="histórico")
"""
    )

    reqs = _extract_requirements_from_builder(tree, "builder.py")

    assert any(req.handler == "_normalize_input_heights" and req.patron == "window._handler()" for req in reqs)
    assert any(req.handler == "_update_responsive_columns" and req.patron == "connect(window._handler)" for req in reqs)
    assert any(req.handler == "_refresh_header_title" and req.patron == "window._handler (atributo)" for req in reqs)
    assert any(req.handler == "_on_confirmar" and req.contexto == "confirmar" for req in reqs)
    assert any(req.handler == "_apply_historico_filters" and req.contexto == "histórico" for req in reqs)
