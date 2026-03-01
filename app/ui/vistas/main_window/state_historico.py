from __future__ import annotations

from typing import Any

from PySide6.QtCore import QItemSelectionModel


def aplicar_filtro_texto_historico(window: Any) -> None:
    window.historico_proxy_model.set_search_text(window.historico_search_input.text())
    window._update_action_state()


def estado_filtro_periodo_historico(window: Any) -> tuple[str, int | None, int | None]:
    if window.historico_periodo_anual_radio.isChecked():
        return "ALL_YEAR", window.historico_periodo_anual_spin.value(), None
    if window.historico_periodo_mes_radio.isChecked():
        return "YEAR_MONTH", window.historico_periodo_mes_ano_spin.value(), window.historico_periodo_mes_combo.currentData()
    return "RANGE", None, None


def actualizar_estado_vacio_historico(window: Any) -> None:
    has_rows = window.historico_proxy_model.rowCount() > 0
    window.historico_empty_state.setVisible(not has_rows)
    window.historico_details_content.setVisible(True)


def manejar_escape_historico(window: Any) -> None:
    if window.historico_search_input.hasFocus():
        window.historico_search_input.clearFocus()
        return
    window.historico_table.clearSelection()


def obtener_solicitudes_historico_seleccionadas(window: Any) -> list[Any]:
    selection = window.historico_table.selectionModel().selectedRows()
    if not selection:
        return []
    solicitudes: list[Any] = []
    for proxy_index in selection:
        source_index = window.historico_proxy_model.mapToSource(proxy_index)
        solicitud = window.historico_model.solicitud_at(source_index.row())
        if solicitud is not None:
            solicitudes.append(solicitud)
    return solicitudes


def obtener_solicitud_historico_seleccionada(window: Any) -> Any | None:
    selected = window._selected_historico_solicitudes()
    return selected[0] if selected else None


def alternar_seleccion_visible_historico(window: Any, checked: bool) -> None:
    selection_model = window.historico_table.selectionModel()
    if selection_model is None:
        return
    flag = QItemSelectionModel.SelectionFlag.Select if checked else QItemSelectionModel.SelectionFlag.Deselect
    for row in range(window.historico_proxy_model.rowCount()):
        index = window.historico_proxy_model.index(row, 0)
        selection_model.select(index, flag | QItemSelectionModel.SelectionFlag.Rows)
    window._update_action_state()


def sincronizar_estado_seleccion_visible_historico(window: Any) -> None:
    if window.historico_select_all_visible_check is None:
        return
    visible_rows = window.historico_proxy_model.rowCount()
    window.historico_select_all_visible_check.blockSignals(True)
    if visible_rows == 0:
        window.historico_select_all_visible_check.setChecked(False)
        window.historico_select_all_visible_check.setEnabled(False)
        window.historico_select_all_visible_check.blockSignals(False)
        return
    selected_count = len(window.historico_table.selectionModel().selectedRows())
    window.historico_select_all_visible_check.setEnabled(True)
    window.historico_select_all_visible_check.setChecked(selected_count == visible_rows)
    window.historico_select_all_visible_check.blockSignals(False)
