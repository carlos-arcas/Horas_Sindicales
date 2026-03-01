from __future__ import annotations

import ast
from pathlib import Path

RUTA_STATE = Path("app/ui/vistas/main_window/state_controller.py")
RUTA_DIALOGOS_COMUNES = Path("app/ui/dialogos_comunes.py")

HELPERS_EXTRAIDOS = {
    "_show_message_with_details",
    "_show_details_dialog",
    "show_message_with_details",
    "show_details_dialog",
}
HELPERS_COMUNES = {"show_message_with_details", "show_details_dialog"}


def _module_function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def _main_window_method_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow":
            return {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
    raise AssertionError("No se encontró la clase MainWindow en state_controller.py")


def _module_class_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.ClassDef)}


def test_state_controller_ya_no_define_helpers_dialogos_genericos() -> None:
    method_names = _main_window_method_names(RUTA_STATE)
    assert HELPERS_EXTRAIDOS.isdisjoint(method_names)


def test_dialogos_comunes_declara_helpers_genericos_reutilizables() -> None:
    function_names = _module_function_names(RUTA_DIALOGOS_COMUNES)
    assert HELPERS_COMUNES.issubset(function_names)


def test_dialogos_comunes_no_duplica_optional_confirm_dialog() -> None:
    class_names = _module_class_names(RUTA_DIALOGOS_COMUNES)
    assert "OptionalConfirmDialog" not in class_names
