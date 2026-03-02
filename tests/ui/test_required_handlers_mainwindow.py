from __future__ import annotations

import ast
from pathlib import Path


FUENTES_HANDLERS = (
    "app/ui/vistas/main_window/state_controller.py",
    "app/ui/vistas/main_window/handlers_formulario.py",
    "app/ui/vistas/main_window/handlers_historico.py",
    "app/ui/vistas/main_window/handlers_layout.py",
    "app/ui/vistas/main_window_vista.py",
)
HANDLERS_REQUERIDOS = (
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


def _read_defined_functions(path: str) -> set[str]:
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=path)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_handlers_minimos_requeridos_en_mainwindow() -> None:
    handlers_definidos: set[str] = set()
    fuentes_existentes = [source for source in FUENTES_HANDLERS if Path(source).exists()]

    for source in fuentes_existentes:
        handlers_definidos.update(_read_defined_functions(source))

    faltantes = [handler for handler in HANDLERS_REQUERIDOS if handler not in handlers_definidos]

    assert not faltantes, (
        "Faltan handlers obligatorios en MainWindow. "
        f"Fuentes revisadas: {', '.join(fuentes_existentes)}. "
        f"Handlers faltantes: {', '.join(faltantes)}"
    )
