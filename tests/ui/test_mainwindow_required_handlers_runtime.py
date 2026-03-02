from __future__ import annotations

import ast
from pathlib import Path


FUENTES_METODOS = (
    Path("app/ui/vistas/main_window/state_controller.py"),
    Path("app/ui/vistas/main_window/handlers_formulario.py"),
    Path("app/ui/vistas/main_window/handlers_historico.py"),
    Path("app/ui/vistas/main_window/handlers_layout.py"),
)
REQUIRED_HANDLERS = (
    "_on_fecha_changed",
    "_update_solicitud_preview",
    "_on_completo_changed",
    "_on_add_pendiente",
    "_apply_historico_default_range",
    "_normalize_input_heights",
    "_update_responsive_columns",
    "_configure_time_placeholders",
    "_on_confirmar",
)


def _defined_method_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            names.update(
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
    return names


def test_mainwindow_define_handlers_requeridos_para_builders() -> None:
    handlers: set[str] = set()
    for source in FUENTES_METODOS:
        handlers.update(_defined_method_names(source))
    faltantes = [name for name in REQUIRED_HANDLERS if name not in handlers]
    assert not faltantes, f"MainWindow no define handlers requeridos: {', '.join(faltantes)}"
