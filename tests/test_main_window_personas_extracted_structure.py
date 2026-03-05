from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers_main_window_ast import (
    es_wrapper_super_minimo,
    metodo_existe_en_mainwindow_o_mixins,
    resolver_metodo_wrapper,
)

ACCIONES_PERSONAS = Path("app/ui/vistas/main_window/acciones_personas.py")

WRAPPER_METHODS = {
    "_is_form_dirty",
    "_confirmar_cambio_delegada",
    "_save_current_draft",
    "_restore_draft_for_persona",
    "_load_personas",
    "_current_persona",
    "_on_persona_changed",
    "_on_add_persona",
    "_on_edit_persona",
    "_on_delete_persona",
    "_sync_config_persona_actions",
    "_selected_config_persona",
    "_on_config_delegada_changed",
    "_restaurar_contexto_guardado",
}

WRAPPER_METHODS_MINIMOS = WRAPPER_METHODS - {"_load_personas"}

EXTRACTED_FUNCTIONS = {
    "is_form_dirty",
    "confirmar_cambio_delegada",
    "save_current_draft",
    "restore_draft_for_persona",
    "load_personas",
    "current_persona",
    "on_persona_changed",
    "on_add_persona",
    "on_edit_persona",
    "on_delete_persona",
    "sync_config_persona_actions",
    "selected_config_persona",
    "on_config_delegada_changed",
    "restaurar_contexto_guardado",
}


def _load_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def test_personas_metodos_existen_en_mainwindow_o_mixins() -> None:
    faltantes = [nombre for nombre in WRAPPER_METHODS if not metodo_existe_en_mainwindow_o_mixins(nombre)]
    assert not faltantes, f"Métodos de personas faltantes en MainWindow/mixins: {faltantes}"



def test_personas_wrappers_en_fachadas_son_minimos() -> None:
    invalidos: list[str] = []
    for method_name in WRAPPER_METHODS_MINIMOS:
        encontrado = resolver_metodo_wrapper(method_name)
        if encontrado is None:
            continue
        if not es_wrapper_super_minimo(encontrado.nodo, method_name):
            invalidos.append(f"{method_name} en {encontrado.archivo}")
    assert not invalidos, "Wrappers no mínimos detectados:\n" + "\n".join(invalidos)



def test_acciones_personas_define_entrypoints() -> None:
    assert ACCIONES_PERSONAS.exists(), "Debe existir acciones_personas.py"
    tree = _load_ast(ACCIONES_PERSONAS)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    for expected in EXTRACTED_FUNCTIONS:
        assert expected in functions
