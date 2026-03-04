from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers_main_window_ast import (
    es_wrapper_super_minimo,
    metodo_existe_en_mainwindow_o_mixins,
    resolver_metodo_wrapper,
)

HISTORICO_ACTIONS = Path("app/ui/vistas/historico_actions.py")

WRAPPER_METHODS = {
    "_apply_historico_text_filter",
    "_historico_period_filter_state",
    "_update_historico_empty_state",
    "_on_historico_escape",
    "_selected_historico",
    "_selected_historico_solicitudes",
    "_on_historico_select_all_visible_toggled",
    "_sync_historico_select_all_visible_state",
    "_notify_historico_filter_if_hidden",
    "_on_export_historico_pdf",
    "_on_eliminar",
}

EXTRACTED_FUNCTIONS = {
    "apply_historico_text_filter",
    "historico_period_filter_state",
    "update_historico_empty_state",
    "on_historico_escape",
    "selected_historico",
    "selected_historico_solicitudes",
    "on_historico_select_all_visible_toggled",
    "sync_historico_select_all_visible_state",
    "notify_historico_filter_if_hidden",
    "on_export_historico_pdf",
    "on_eliminar",
}


def _load_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def test_historico_metodos_existen_en_mainwindow_o_mixins() -> None:
    faltantes = [nombre for nombre in WRAPPER_METHODS if not metodo_existe_en_mainwindow_o_mixins(nombre)]
    assert not faltantes, f"Métodos de histórico faltantes en MainWindow/mixins: {faltantes}"



def test_historico_wrappers_en_fachadas_son_minimos() -> None:
    invalidos: list[str] = []
    for method_name in WRAPPER_METHODS:
        encontrado = resolver_metodo_wrapper(method_name)
        if encontrado is None:
            continue
        if not es_wrapper_super_minimo(encontrado.nodo, method_name):
            invalidos.append(f"{method_name} en {encontrado.archivo}")
    assert not invalidos, "Wrappers no mínimos detectados:\n" + "\n".join(invalidos)



def test_historico_actions_define_extracted_entrypoints() -> None:
    tree = _load_ast(HISTORICO_ACTIONS)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    for expected in EXTRACTED_FUNCTIONS:
        assert expected in functions
