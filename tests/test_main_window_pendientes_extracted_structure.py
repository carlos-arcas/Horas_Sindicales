from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers_main_window_ast import (
    es_wrapper_super_minimo,
    metodo_existe_en_mainwindow_o_mixins,
    resolver_metodo_wrapper,
)

PENDIENTES_ACTIONS = Path("app/ui/vistas/main_window/acciones_pendientes.py")

WRAPPER_METHODS = {
    "_selected_pending_row_indexes",
    "_selected_pending_for_editing",
    "_find_pending_row_by_id",
    "_focus_pending_row",
    "_focus_pending_by_id",
    "_on_review_hidden_pendientes",
    "_on_remove_huerfana",
    "_clear_pendientes",
    "_update_pending_totals",
    "_refresh_pending_conflicts",
    "_refresh_pending_ui_state",
}

EXTRACTED_FUNCTIONS = {
    "helper_selected_pending_row_indexes",
    "helper_selected_pending_for_editing",
    "helper_find_row_by_id",
    "helper_focus_pending_row",
    "helper_focus_pending_by_id",
    "on_review_hidden",
    "on_remove_huerfana",
    "on_clear_pendientes",
    "helper_update_pending_totals",
    "helper_refresh_pending_conflicts",
    "helper_refresh_pending_ui_state",
}


def _load_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def test_pendientes_metodos_existen_en_mainwindow_o_mixins() -> None:
    faltantes = [nombre for nombre in WRAPPER_METHODS if not metodo_existe_en_mainwindow_o_mixins(nombre)]
    assert not faltantes, f"Métodos de pendientes faltantes en MainWindow/mixins: {faltantes}"



def test_pendientes_wrappers_en_fachadas_son_minimos() -> None:
    invalidos: list[str] = []
    for method_name in WRAPPER_METHODS:
        encontrado = resolver_metodo_wrapper(method_name)
        if encontrado is None:
            continue
        if not es_wrapper_super_minimo(encontrado.nodo, method_name):
            invalidos.append(f"{method_name} en {encontrado.archivo}")
    assert not invalidos, "Wrappers no mínimos detectados:\n" + "\n".join(invalidos)



def test_acciones_pendientes_define_extracted_entrypoints() -> None:
    tree = _load_ast(PENDIENTES_ACTIONS)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    for expected in EXTRACTED_FUNCTIONS:
        assert expected in functions
        assert expected.startswith(("on_", "helper_")), (
            "acciones_pendientes.py solo debe exponer nombres on_* / helper_* para esta extracción"
        )
