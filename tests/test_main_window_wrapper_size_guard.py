from __future__ import annotations

import ast

from tests.helpers_main_window_ast import (
    ROOT,
    es_wrapper_super_minimo,
    metodo_existe_en_mainwindow_o_mixins,
    resolver_metodo_wrapper,
)

ARCHIVO_STATE_CONTROLLER = ROOT / "app/ui/vistas/main_window/state_controller.py"
ARCHIVO_MAIN_WINDOW_VISTA = ROOT / "app/ui/vistas/main_window_vista.py"
RUTAS_WIRING = (ROOT / "app/ui/vistas/builders", ROOT / "app/ui/vistas/main_window")

CRITICAL_WRAPPERS = {
    "_apply_sync_report",
    "_show_sync_details_dialog",
    "_on_sync_finished",
    "_on_sync_failed",
    "_on_sync",
    "_on_simulate_sync",
    "_on_confirm_sync",
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

LIMITE_LOC_STATE_CONTROLLER = 450
LIMITE_LOC_MAIN_WINDOW_VISTA = 470


def _extraer_handlers_wiring() -> set[str]:
    handlers: set[str] = set()
    for base in RUTAS_WIRING:
        for archivo in sorted(base.rglob("*.py")):
            tree = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "connect":
                    if not node.args:
                        continue
                    arg0 = node.args[0]
                    if isinstance(arg0, ast.Attribute) and isinstance(arg0.value, ast.Name) and arg0.value.id == "window":
                        handlers.add(arg0.attr)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "conectar_signal":
                    if len(node.args) > 2 and isinstance(node.args[2], ast.Constant) and isinstance(node.args[2].value, str):
                        handlers.add(node.args[2].value)
                    for keyword in node.keywords:
                        if keyword.arg == "handler_name" and isinstance(keyword.value, ast.Constant):
                            if isinstance(keyword.value.value, str):
                                handlers.add(keyword.value.value)
    return handlers



def test_main_window_critical_wrappers_stay_minimal() -> None:
    wiring_handlers = _extraer_handlers_wiring()
    wrappers_obligatorios = sorted(CRITICAL_WRAPPERS & wiring_handlers)
    faltantes: list[str] = []
    invalidos: list[str] = []
    faltan_en_mixins: list[str] = []

    for name in wrappers_obligatorios:
        wrapper = resolver_metodo_wrapper(name)
        if wrapper is None:
            faltantes.append(name)
            continue
        if not es_wrapper_super_minimo(wrapper.nodo, name):
            invalidos.append(f"{name} en {wrapper.archivo}")

    for name in sorted(CRITICAL_WRAPPERS - set(wrappers_obligatorios)):
        if metodo_existe_en_mainwindow_o_mixins(name):
            continue
        faltan_en_mixins.append(name)

    assert not faltantes, f"Wrappers críticos de wiring faltantes en fachadas MainWindow: {faltantes}"
    assert not invalidos, "Wrappers críticos deben delegar con super() y ser mínimos:\n" + "\n".join(invalidos)
    assert not faltan_en_mixins, f"Métodos críticos faltantes incluso en mixins: {faltan_en_mixins}"



def test_main_window_wrapper_files_siguen_delgados() -> None:
    state_loc = len(ARCHIVO_STATE_CONTROLLER.read_text(encoding="utf-8").splitlines())
    vista_loc = len(ARCHIVO_MAIN_WINDOW_VISTA.read_text(encoding="utf-8").splitlines())
    assert state_loc <= LIMITE_LOC_STATE_CONTROLLER, f"state_controller.py excede límite: {state_loc} LOC"
    assert vista_loc <= LIMITE_LOC_MAIN_WINDOW_VISTA, f"main_window_vista.py excede límite: {vista_loc} LOC"
