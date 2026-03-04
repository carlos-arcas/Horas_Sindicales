from __future__ import annotations

import ast
from pathlib import Path

from tests.helpers_main_window_ast import (
    es_wrapper_super_minimo,
    metodo_existe_en_mainwindow_o_mixins,
    resolver_metodo_wrapper,
)

ACCIONES_SYNC = Path("app/ui/vistas/main_window/acciones_sincronizacion.py")
METODOS_SYNC = {
    "_apply_sync_report",
    "_show_sync_details_dialog",
    "_on_sync_finished",
    "_on_sync_failed",
}


def _load_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def test_sync_metodos_existen_en_mainwindow_o_mixins() -> None:
    faltantes = [nombre for nombre in METODOS_SYNC if not metodo_existe_en_mainwindow_o_mixins(nombre)]
    assert not faltantes, f"Métodos sync faltantes en MainWindow/mixins: {faltantes}"



def test_sync_wrappers_en_fachadas_son_minimos() -> None:
    invalidos: list[str] = []
    for method_name in METODOS_SYNC:
        encontrado = resolver_metodo_wrapper(method_name)
        if encontrado is None:
            continue
        if not es_wrapper_super_minimo(encontrado.nodo, method_name):
            invalidos.append(f"{method_name} en {encontrado.archivo}")
    assert not invalidos, "Wrappers no mínimos detectados:\n" + "\n".join(invalidos)



def test_acciones_sincronizacion_define_entrypoints() -> None:
    assert ACCIONES_SYNC.exists(), "Debe existir acciones_sincronizacion.py"
    tree = _load_ast(ACCIONES_SYNC)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

    for expected in {"on_sync", "on_sync_finished", "apply_sync_report"}:
        assert expected in functions
