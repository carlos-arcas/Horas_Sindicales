from __future__ import annotations

import logging

from typing import TYPE_CHECKING

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QItemSelectionModel
    from PySide6.QtWidgets import QAbstractItemView
except Exception:  # pragma: no cover - habilita import en entornos CI sin Qt
    QApplication = QAbstractItemView = QItemSelectionModel = Qt = object

from app.ui.vistas.seleccion_pendientes import (
    ESTADO_TOGGLE_MARCADO,
    ESTADO_TOGGLE_PARCIAL,
    construir_rango_contiguo,
    resolver_estado_toggle,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.application.dto import SolicitudDTO
    from app.ui.vistas.main_window.state_controller import MainWindow


def obtener_indices_filas_pendientes_seleccionadas(window: MainWindow) -> list[int]:
    selection_model = window.pendientes_table.selectionModel()
    if selection_model is None:
        return []
    return sorted(
        {
            index.row()
            for index in selection_model.selectedRows()
            if _fila_visible_y_marcable(window, index.row())
        }
    )


def alternar_seleccion_visible_pendientes(window: MainWindow, checked: bool) -> None:
    selection_model = window.pendientes_table.selectionModel()
    model = window.pendientes_table.model()
    if selection_model is None or model is None:
        return

    filas_visibles = _filas_visibles_marcables(window)
    logger.info(
        "UI_PENDIENTES_BULK_MARCAR_VISIBLES",
        extra={
            "checked": bool(checked),
            "filas_visibles_marcables": len(filas_visibles),
            "filas_marcadas_previas": len(obtener_indices_filas_pendientes_seleccionadas(window)),
        },
    )
    flag = QItemSelectionModel.SelectionFlag.Select if checked else QItemSelectionModel.SelectionFlag.Deselect
    window._pending_bulk_selection_in_progress = True
    try:
        for fila in filas_visibles:
            index = model.index(fila, 0)
            selection_model.select(index, flag | QItemSelectionModel.SelectionFlag.Rows)
    finally:
        window._pending_bulk_selection_in_progress = False
    sincronizar_estado_seleccion_visible_pendientes(window)


def sincronizar_estado_seleccion_visible_pendientes(window: MainWindow) -> None:
    toggle = getattr(window, "pending_select_all_visible_check", None)
    if toggle is None:
        return

    filas_visibles = _filas_visibles_marcables(window)
    toggle.blockSignals(True)
    if not filas_visibles:
        toggle.setEnabled(False)
        toggle.setCheckState(Qt.CheckState.Unchecked)
        toggle.blockSignals(False)
        return

    seleccionadas = len(obtener_indices_filas_pendientes_seleccionadas(window))
    estado = resolver_estado_toggle(len(filas_visibles), seleccionadas)
    toggle.setEnabled(True)
    if estado == ESTADO_TOGGLE_MARCADO:
        toggle.setCheckState(Qt.CheckState.Checked)
    elif estado == ESTADO_TOGGLE_PARCIAL:
        toggle.setCheckState(Qt.CheckState.PartiallyChecked)
    else:
        toggle.setCheckState(Qt.CheckState.Unchecked)
    toggle.blockSignals(False)


def manejar_click_fila_pendiente(window: MainWindow, index: object) -> None:
    fila_destino = getattr(index, "row", lambda: -1)()
    if not isinstance(fila_destino, int) or fila_destino < 0:
        return

    if not _fila_visible_y_marcable(window, fila_destino):
        return

    fila_ancla = getattr(window, "_pending_selection_anchor_row", None)
    if not _tiene_shift_presionado() or not isinstance(fila_ancla, int):
        window._pending_selection_anchor_row = fila_destino
        return

    selection_model = window.pendientes_table.selectionModel()
    model = window.pendientes_table.model()
    if selection_model is None or model is None:
        window._pending_selection_anchor_row = fila_destino
        return

    filas_visibles = _filas_visibles_marcables(window)
    filas_rango = construir_rango_contiguo(
        filas_visibles_marcables=filas_visibles,
        fila_ancla=fila_ancla,
        fila_destino=fila_destino,
    )
    logger.info(
        "UI_PENDIENTES_SHIFT_RANGE",
        extra={
            "fila_ancla": fila_ancla,
            "fila_destino": fila_destino,
            "rango_aplicado": filas_rango,
        },
    )
    destino_index = model.index(fila_destino, 0)
    destino_marcado = selection_model.isSelected(destino_index)
    flag = QItemSelectionModel.SelectionFlag.Select if destino_marcado else QItemSelectionModel.SelectionFlag.Deselect
    for fila in filas_rango:
        fila_index = model.index(fila, 0)
        selection_model.select(fila_index, flag | QItemSelectionModel.SelectionFlag.Rows)

    window._pending_selection_anchor_row = fila_destino
    sincronizar_estado_seleccion_visible_pendientes(window)


def obtener_pendiente_para_edicion(window: MainWindow) -> SolicitudDTO | None:
    rows = obtener_indices_filas_pendientes_seleccionadas(window)
    if len(rows) != 1:
        return None
    row = rows[0]
    if row < 0 or row >= len(window._pending_solicitudes):
        return None
    return window._pending_solicitudes[row]


def buscar_fila_pendiente_por_id(window: MainWindow, solicitud_id: int | None) -> int | None:
    if solicitud_id is None:
        return None
    for row, pending in enumerate(window._pending_solicitudes):
        if pending.id == solicitud_id:
            return row
    return None


def enfocar_fila_pendiente(window: MainWindow, row: int) -> None:
    if row < 0 or row >= window.pendientes_model.rowCount():
        return
    window.pendientes_table.selectRow(row)
    model_index = window.pendientes_model.index(row, 0)
    window.pendientes_table.scrollTo(model_index, QAbstractItemView.PositionAtCenter)
    window.pendientes_table.setFocus()


def enfocar_pendiente_por_id(window: MainWindow, solicitud_id: int | None) -> bool:
    row = buscar_fila_pendiente_por_id(window, solicitud_id)
    if row is None:
        return False
    enfocar_fila_pendiente(window, row)
    return True


def _filas_visibles_marcables(window: MainWindow) -> list[int]:
    model = window.pendientes_table.model()
    if model is None:
        return []
    return [fila for fila in range(model.rowCount()) if _fila_visible_y_marcable(window, fila)]


def _fila_visible_y_marcable(window: MainWindow, fila: int) -> bool:
    model = window.pendientes_table.model()
    if model is None or fila < 0 or fila >= model.rowCount():
        return False
    if window.pendientes_table.isRowHidden(fila):
        return False
    index = model.index(fila, 0)
    flags = model.flags(index)
    return bool(flags & Qt.ItemFlag.ItemIsEnabled and flags & Qt.ItemFlag.ItemIsSelectable)


def _tiene_shift_presionado() -> bool:
    modifiers = QApplication.keyboardModifiers()
    return bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
