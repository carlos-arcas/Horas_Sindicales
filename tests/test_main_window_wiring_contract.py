from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_WIRING_HANDLERS = (
    "_on_completo_changed",
    "_on_add_pendiente",
    "_on_confirmar",
    "_update_solicitud_preview",
    "_apply_historico_default_range",
    "_status_to_label",
    "_normalize_input_heights",
    "_update_responsive_columns",
    "_configure_time_placeholders",
    "_configure_operativa_focus_order",
    "_configure_historico_focus_order",
)


def _class_methods(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
    return set()


def test_main_window_declara_handlers_minimos_de_wiring() -> None:
    vista_methods = _class_methods(ROOT / "app/ui/vistas/main_window_vista.py", "MainWindow")
    base_methods = _class_methods(
        ROOT / "app/ui/vistas/main_window/state_controller.py", "MainWindow"
    )
    declared_methods = vista_methods | base_methods
    missing = [name for name in REQUIRED_WIRING_HANDLERS if name not in declared_methods]
    assert not missing, (
        "MainWindow no cumple el contrato mínimo de handlers requerido por builders: "
        + ", ".join(missing)
    )
