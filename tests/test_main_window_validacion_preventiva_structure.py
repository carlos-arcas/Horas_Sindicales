from __future__ import annotations

import ast
from pathlib import Path

STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")
VALIDACION_PREVENTIVA = Path("app/ui/vistas/main_window/validacion_preventiva.py")


def _load_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def _method_sizes(class_node: ast.ClassDef) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef):
            sizes[node.name] = (node.end_lineno or node.lineno) - node.lineno + 1
    return sizes


def test_state_controller_preventive_validation_methods_are_wrappers() -> None:
    tree = _load_ast(STATE_CONTROLLER)
    class_node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    sizes = _method_sizes(class_node)

    wrapper_methods = (
        "_bind_preventive_validation_events",
        "_mark_field_touched",
        "_schedule_preventive_validation",
        "_run_preventive_validation",
        "_collect_base_preventive_errors",
        "_collect_preventive_validation",
        "_collect_preventive_business_rules",
        "_collect_pending_duplicates_warning",
        "_on_go_to_existing_duplicate",
        "_render_preventive_validation",
        "_run_preconfirm_checks",
    )
    for method_name in wrapper_methods:
        assert method_name in sizes
        assert sizes[method_name] <= 8, f"{method_name} debe ser wrapper de pocas líneas"


def test_validacion_preventiva_module_entrypoints_exist() -> None:
    assert VALIDACION_PREVENTIVA.exists(), "Debe existir validacion_preventiva.py"
    tree = _load_ast(VALIDACION_PREVENTIVA)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    expected = {
        "es_fecha_iso_valida",
        "validar_tramo_preventivo",
        "_bind_preventive_validation_events",
        "_mark_field_touched",
        "_schedule_preventive_validation",
        "_run_preventive_validation",
        "_collect_base_preventive_errors",
        "_collect_preventive_business_rules",
        "_collect_pending_duplicates_warning",
        "_collect_preventive_validation",
        "_render_preventive_validation",
        "_on_go_to_existing_duplicate",
        "_run_preconfirm_checks",
    }
    for name in expected:
        assert name in functions
