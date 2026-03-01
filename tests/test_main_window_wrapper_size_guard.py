from __future__ import annotations

import ast
from pathlib import Path

STATE_CONTROLLER = Path("app/ui/vistas/main_window/state_controller.py")

CRITICAL_WRAPPERS = {
    # Sync wrappers (modulo extraído)
    "_apply_sync_report",
    "_show_sync_details_dialog",
    "_on_sync_finished",
    "_on_sync_failed",
    "_on_sync",
    "_on_simulate_sync",
    "_on_confirm_sync",
    # Histórico wrappers (modulo extraído)
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
    # Pendientes wrappers (modulo extraído)
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


def _load_main_window_methods() -> dict[str, ast.FunctionDef]:
    tree = ast.parse(STATE_CONTROLLER.read_text(encoding="utf-8"))
    class_node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    return {node.name: node for node in class_node.body if isinstance(node, ast.FunctionDef)}


def test_main_window_critical_wrappers_stay_minimal() -> None:
    methods = _load_main_window_methods()

    missing = sorted(name for name in CRITICAL_WRAPPERS if name not in methods)
    assert not missing, f"Wrappers críticos faltantes en MainWindow: {missing}"

    oversized = {
        name: len(methods[name].body)
        for name in CRITICAL_WRAPPERS
        if len(methods[name].body) > 3
    }
    assert not oversized, f"Wrappers críticos deben tener 1-3 statements: {oversized}"
