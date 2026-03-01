from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from PySide6.QtWidgets import QAbstractItemView
except Exception:  # pragma: no cover - habilita import en entornos CI sin Qt
    QAbstractItemView = object

if TYPE_CHECKING:
    from app.application.dto import SolicitudDTO
    from app.ui.vistas.main_window.state_controller import MainWindow


def obtener_indices_filas_pendientes_seleccionadas(window: MainWindow) -> list[int]:
    selection_model = window.pendientes_table.selectionModel()
    if selection_model is None:
        return []
    return sorted({index.row() for index in selection_model.selectedRows()})


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
