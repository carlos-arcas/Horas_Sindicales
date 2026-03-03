from __future__ import annotations

from typing import Any

from PySide6.QtCore import QDate, QItemSelectionModel

from app.core.observability import OperationContext
from app.ui.copy_catalog import copy_text


def aplicar_rango_por_defecto_historico(window: Any) -> None:
    today = QDate.currentDate()
    window.historico_desde_date.setDate(today.addDays(-30))
    window.historico_hasta_date.setDate(today)

    if getattr(window, "historico_periodo_rango_radio", None) is not None:
        window.historico_periodo_rango_radio.setChecked(True)

    apply_filters = getattr(window, "_apply_historico_filters", None)
    if callable(apply_filters) and getattr(window, "historico_proxy_model", None) is not None:
        apply_filters()


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
    selection_model = window.historico_table.selectionModel()
    if selection_model is None:
        return []
    selection = selection_model.selectedRows()
    if not selection:
        return []
    solicitudes: list[Any] = []
    for proxy_index in selection:
        source_index = window.historico_proxy_model.mapToSource(proxy_index)
        solicitud = window.historico_model.solicitud_at(source_index.row())
        if solicitud is not None:
            solicitudes.append(solicitud)
    return solicitudes


def obtener_ids_solicitudes_historico_seleccionadas(window: Any) -> set[int]:
    selection_model = window.historico_table.selectionModel()
    if selection_model is None:
        return set()
    selection = selection_model.selectedRows()
    if not selection:
        return set()

    ids: set[int] = set()
    for proxy_index in selection:
        source_index = window.historico_proxy_model.mapToSource(proxy_index)
        if not hasattr(source_index, "isValid") or not source_index.isValid():
            continue
        solicitud = window.historico_model.solicitud_at(source_index.row())
        solicitud_id = getattr(solicitud, "id", None)
        if isinstance(solicitud_id, int):
            ids.add(solicitud_id)
    return ids


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
    selection_model = window.historico_table.selectionModel()
    selected_count = len(selection_model.selectedRows()) if selection_model is not None else 0
    window.historico_select_all_visible_check.setEnabled(True)
    window.historico_select_all_visible_check.setChecked(selected_count == visible_rows)
    window.historico_select_all_visible_check.blockSignals(False)


def actualizar_estado_seleccion_historico(window: Any) -> None:
    window._historico_ids_seleccionados = obtener_ids_solicitudes_historico_seleccionadas(window)
    if getattr(window, "eliminar_button", None) is not None:
        window.eliminar_button.setText(copy_text("ui.historico.eliminar_boton").format(n=len(window._historico_ids_seleccionados)))


def eliminar_historico_seleccionado(window: Any) -> int:
    ids_seleccionados = set(getattr(window, "_historico_ids_seleccionados", set()))
    if not ids_seleccionados:
        return 0

    for solicitud_id in sorted(ids_seleccionados):
        with OperationContext("eliminar_solicitud") as operation:
            window._solicitud_use_cases.eliminar_solicitud(solicitud_id, correlation_id=operation.correlation_id)

    window._historico_ids_seleccionados = set()
    clear_selection = getattr(getattr(window, "historico_table", None), "clearSelection", None)
    if callable(clear_selection):
        clear_selection()
    if getattr(window, "eliminar_button", None) is not None:
        window.eliminar_button.setText(copy_text("ui.historico.eliminar_boton").format(n=0))
    return len(ids_seleccionados)
