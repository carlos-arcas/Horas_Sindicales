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
STATE_CONTROLLER = "app/ui/vistas/main_window/state_controller.py"


@dataclass(frozen=True)
class HandlerRequirement:
    builder: str
    line: int
    handler: str
    contexto: str


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
        if isinstance(node, ast.Attribute) and _is_window_handler_attr(node):
            handlers.add(node.attr)
    return handlers


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


def _extract_conectar_signal_handler_requirements(tree: ast.AST, builder: str) -> list[HandlerRequirement]:
    requirements: list[HandlerRequirement] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_conectar_signal_call(node):
            continue
        handler = _extract_handler_name_from_call(node)
        if handler is None:
            continue
        requirements.append(
            HandlerRequirement(
                builder=builder,
                line=node.lineno,
                handler=handler,
                contexto=_extract_contexto_from_call(node),
            )
        )
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


def _format_missing_requirements(missing: list[HandlerRequirement]) -> str:
    ordered = sorted(missing, key=lambda item: (item.builder, item.line, item.handler, item.contexto))
    lines = [
        f"- {item.builder}:{item.line} | handler={item.handler} | contexto={item.contexto}"
        for item in ordered
    ]
    return "Faltan handlers requeridos por conectar_signal\n" + "\n".join(lines)


def test_builders_referencian_handlers_presentes_en_state_controller_ast() -> None:
    handlers_referenciados: set[str] = set()
    requirements: list[HandlerRequirement] = []

    for builder, tree in _collect_builder_trees():
        handlers_referenciados.update(_extract_window_handlers_from_ast(tree))
        requirements.extend(_extract_conectar_signal_handler_requirements(tree, builder))

    handlers_referenciados.update(req.handler for req in requirements)
    handlers_definidos = _extract_defined_functions_from_ast(_read_ast(STATE_CONTROLLER))

    faltantes = sorted(handler for handler in handlers_referenciados if handler not in handlers_definidos)

    assert not faltantes, (
        "Handlers faltantes en state_controller.py detectados desde builders "
        f"(calls/callbacks y conectar_signal): {', '.join(faltantes)}"
    )


def test_conectar_signal_handler_name_literal_debe_existir_en_state_controller() -> None:
    handlers_definidos = _extract_defined_functions_from_ast(_read_ast(STATE_CONTROLLER))
    missing: list[HandlerRequirement] = []

    for builder, tree in _collect_builder_trees():
        for req in _extract_conectar_signal_handler_requirements(tree, builder):
            if req.handler not in handlers_definidos:
                missing.append(req)

    assert not missing, _format_missing_requirements(missing)


def test_extractor_detecta_llamadas_y_callbacks_status_to_label() -> None:
    tree = ast.parse(
        """
window._status_to_label("IDLE")
button.clicked.connect(window._status_to_label)
conectar_signal(window, signal, "_status_to_label", contexto="estado")
conectar_signal(window, signal, handler_name="_save", contexto="guardar")
"""
    )

    handlers = _extract_window_handlers_from_ast(tree)
    reqs = _extract_conectar_signal_handler_requirements(tree, "builder.py")

    assert "_status_to_label" in handlers
    assert any(req.handler == "_status_to_label" and req.contexto == "estado" for req in reqs)
    assert any(req.handler == "_save" and req.contexto == "guardar" for req in reqs)
