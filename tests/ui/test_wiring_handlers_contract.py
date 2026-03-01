from __future__ import annotations

import ast
import re
from pathlib import Path

BUILDERS = (
    Path("app/ui/vistas/builders/builders_formulario_solicitud.py"),
    Path("app/ui/vistas/builders/builders_tablas.py"),
    Path("app/ui/vistas/builders/builders_sync_panel.py"),
    Path("app/ui/vistas/builders/builders_barra_superior.py"),
)
STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")
CONNECT_PATTERN = re.compile(r"\.connect\(window\.([A-Za-z_][A-Za-z0-9_]*)")
HANDLER_PATTERN = re.compile(r"^_(?:on|update|apply|run)_")


def _extract_builder_handlers() -> set[str]:
    handlers: set[str] = set()
    for builder_path in BUILDERS:
        contenido = builder_path.read_text(encoding="utf-8")
        for nombre in CONNECT_PATTERN.findall(contenido):
            if HANDLER_PATTERN.match(nombre):
                handlers.add(nombre)
    return handlers


def _extract_main_window_methods() -> set[str]:
    tree = ast.parse(STATE_CONTROLLER.read_text(encoding="utf-8"))
    clase = next(
        nodo for nodo in tree.body if isinstance(nodo, ast.ClassDef) and nodo.name == "MainWindow"
    )
    return {nodo.name for nodo in clase.body if isinstance(nodo, ast.FunctionDef)}


def test_builders_connect_only_main_window_declared_handlers() -> None:
    handlers = _extract_builder_handlers()
    methods = _extract_main_window_methods()

    faltantes = sorted(nombre for nombre in handlers if nombre not in methods)
    assert not faltantes, (
        "Contrato de wiring roto: handlers conectados en builders no declarados en MainWindow: "
        f"{faltantes}"
    )
