from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from app.application.use_cases.solicitudes.validaciones import detectar_duplicados_en_pendientes
from app.core.observability import OperationContext
from app.domain.services import BusinessRuleError, ValidacionError
from app.ui.copy_catalog import copy_text
from app.ui.notification_service import OperationFeedback
from app.ui.vistas.pending_duplicate_presenter import PendingDuplicateEntrada, resolve_pending_duplicate_row

try:
    from PySide6.QtWidgets import QAbstractItemView, QMessageBox
except Exception:  # pragma: no cover - habilita import en entornos CI sin Qt
    QAbstractItemView = QMessageBox = object

if TYPE_CHECKING:
    from app.application.dto import SolicitudDTO
    from app.ui.vistas.main_window.state_controller import MainWindow


logger = logging.getLogger(__name__)


def helper_selected_pending_row_indexes(window: MainWindow) -> list[int]:
    selection_model = window.pendientes_table.selectionModel()
    if selection_model is None:
        return []
    return sorted({index.row() for index in selection_model.selectedRows()})


def helper_selected_pending_for_editing(window: MainWindow) -> SolicitudDTO | None:
    rows = helper_selected_pending_row_indexes(window)
    if len(rows) != 1:
        return None
    row = rows[0]
    if row < 0 or row >= len(window._pending_solicitudes):
        return None
    return window._pending_solicitudes[row]


def helper_find_row_by_id(window: MainWindow, solicitud_id: int | None) -> int | None:
    if solicitud_id is None:
        return None
    for row, pending in enumerate(window._pending_solicitudes):
        if pending.id == solicitud_id:
            return row
    return None


def helper_focus_pending_row(window: MainWindow, row: int) -> None:
    if row < 0 or row >= window.pendientes_model.rowCount():
        return
    window.pendientes_table.selectRow(row)
    model_index = window.pendientes_model.index(row, 0)
    window.pendientes_table.scrollTo(model_index, QAbstractItemView.PositionAtCenter)
    window.pendientes_table.setFocus()


def helper_focus_pending_by_id(window: MainWindow, solicitud_id: int | None) -> bool:
    row = helper_find_row_by_id(window, solicitud_id)
    if row is None:
        return False
    helper_focus_pending_row(window, row)
    return True


def helper_update_pending_totals(window: MainWindow) -> None:
    persona = window._current_persona()
    total_min = 0
    if persona is not None and window._pending_solicitudes:
        try:
            total_min = window._solicitud_use_cases.sumar_pendientes_min(persona.id or 0, window._pending_solicitudes)
        except BusinessRuleError:
            total_min = 0
    formatted = window._format_minutes(total_min)
    window.total_pendientes_label.setText(f"Total: {formatted}")
    if window.status_pending_label is not None:
        window.status_pending_label.setText(f"Pendiente: {formatted}")
    window.statusBar().showMessage(f"Pendiente: {formatted}", 4000)


def helper_refresh_pending_conflicts(window: MainWindow) -> None:
    conflict_rows: set[int] = set()
    if window._pending_solicitudes:
        try:
            conflict_rows = window._solicitud_use_cases.detectar_conflictos_pendientes(window._pending_solicitudes)
        except BusinessRuleError as exc:
            logger.warning("No se pudieron calcular conflictos de pendientes: %s", exc)

    previously_conflicting = bool(window._pending_conflict_rows)
    window._pending_conflict_rows = conflict_rows
    window.pendientes_model.set_conflict_rows(conflict_rows)

    if conflict_rows and not previously_conflicting:
        window.toast.warning(
            "Hay peticiones con horarios solapados. Elimina/modifica el conflicto para confirmar.",
            title="Conflictos detectados",
        )


def helper_refresh_pending_ui_state(window: MainWindow) -> None:
    window.pendientes_model.set_show_delegada(window._pending_view_all)
    window.pendientes_model.set_solicitudes(window._pending_solicitudes)
    window._configure_solicitudes_table(window.pendientes_table)
    helper_update_pending_totals(window)
    helper_refresh_pending_conflicts(window)
    window._update_action_state()
    window._update_global_context()


def on_clear_pendientes(window: MainWindow) -> None:
    window._pending_solicitudes = []
    window._pending_all_solicitudes = []
    window._hidden_pendientes = []
    window._orphan_pendientes = []
    window.pendientes_model.clear()
    window.huerfanas_model.clear()
    window._pending_conflict_rows = set()
    helper_update_pending_totals(window)
    window._update_action_state()


def on_review_hidden(window: MainWindow) -> None:
    if not window._hidden_pendientes:
        return
    first_hidden = window._hidden_pendientes[0]
    window.ver_todas_pendientes_button.setChecked(True)
    window._reload_pending_views()
    helper_focus_pending_by_id(window, first_hidden.id)


def on_remove_huerfana(window: MainWindow) -> None:
    selection = window.huerfanas_table.selectionModel().selectedRows()
    if not selection:
        return
    row = selection[0].row()
    if row < 0 or row >= len(window._orphan_pendientes):
        return
    solicitud = window._orphan_pendientes[row]
    if solicitud.id is None:
        return
    window._solicitud_use_cases.eliminar_solicitud(solicitud.id)
    window._reload_pending_views()


def helper_selected_pending_solicitudes(window: MainWindow) -> list[SolicitudDTO]:
    selected_rows = helper_selected_pending_row_indexes(window)
    return [window._pending_solicitudes[row] for row in selected_rows if 0 <= row < len(window._pending_solicitudes)]


def helper_find_pending_duplicate_row(window: MainWindow, solicitud: SolicitudDTO) -> int | None:
    editing = helper_selected_pending_for_editing(window)
    editing_id = getattr(editing, "id", None)
    selected_rows = helper_selected_pending_row_indexes(window)
    editing_row = selected_rows[0] if selected_rows else None
    decision = resolve_pending_duplicate_row(
        PendingDuplicateEntrada(
            solicitud=solicitud,
            pending_solicitudes=window._pending_solicitudes,
            editing_pending_id=editing_id,
            editing_row=editing_row,
            duplicated_keys=detectar_duplicados_en_pendientes(window._pending_solicitudes),
        )
    )
    logger.info(
        "UI_PREVENTIVE_DUPLICATE_RESULT duplicate_row=%s editing_id=%s editing_row=%s reason=%s",
        decision.row_index,
        editing_id,
        editing_row,
        decision.reason_code,
    )
    return decision.row_index


def on_handle_duplicate_before_add(window: MainWindow, duplicate_row: int) -> bool:
    dialog = QMessageBox(window)
    dialog.setWindowTitle("Pendiente duplicada")
    dialog.setText("Ya existe una pendiente igual para esta delegada, fecha y tramo horario.")
    dialog.setInformativeText("Puedes ir a la existente o crear igualmente.")
    goto_button = dialog.addButton("Ir a la pendiente existente", QMessageBox.AcceptRole)
    create_button = dialog.addButton("Crear igualmente", QMessageBox.ActionRole)
    cancel_button = dialog.addButton("Cancelar", QMessageBox.RejectRole)
    create_button.setEnabled(False)
    create_button.setToolTip("No permitido por la regla de negocio de duplicados.")
    dialog.exec()
    clicked = dialog.clickedButton()
    if clicked is goto_button:
        helper_focus_pending_row(window, duplicate_row)
        return False
    if clicked is create_button:
        return True
    if clicked is cancel_button:
        return False
    return False


def on_resolve_pending_conflict(window: MainWindow, fecha_pedida: str, completo: bool) -> bool:
    conflictos = [
        index
        for index, solicitud in enumerate(window._pending_solicitudes)
        if solicitud.fecha_pedida == fecha_pedida and solicitud.completo != completo
    ]
    if not conflictos:
        return True
    mensaje = (
        "Hay horas parciales. ¿Sustituirlas por COMPLETO?"
        if completo
        else "Ya existe un COMPLETO. ¿Sustituirlo por esta franja?"
    )
    if not window._confirm_conflicto(mensaje):
        return False
    for index in sorted(conflictos, reverse=True):
        window._pending_solicitudes.pop(index)
    helper_refresh_pending_ui_state(window)
    return True


def helper_pending_minutes_for_period(window: MainWindow, filtro) -> int:
    persona = window._current_persona()
    if persona is None or not window._pending_solicitudes:
        return 0
    pendientes_filtrados = []
    for solicitud in window._pending_solicitudes:
        fecha = datetime.strptime(solicitud.fecha_pedida, "%Y-%m-%d")
        if fecha.year != filtro.year:
            continue
        if filtro.modo == "MENSUAL" and fecha.month != filtro.month:
            continue
        pendientes_filtrados.append(solicitud)
    if not pendientes_filtrados:
        return 0
    try:
        return window._solicitud_use_cases.sumar_pendientes_min(persona.id or 0, pendientes_filtrados)
    except BusinessRuleError:
        return 0


def on_add_pendiente(window: MainWindow, *args, **kwargs) -> None:
    _ = (args, kwargs)
    controller = getattr(window, "_solicitudes_controller", None)
    if controller is not None and hasattr(controller, "on_add_pendiente"):
        controller.on_add_pendiente()
        return

    solicitud = window._build_preview_solicitud()
    if solicitud is None:
        return

    notas_text = window.notas_input.toPlainText().strip()
    if notas_text:
        solicitud = solicitud.model_copy(update={"notas": notas_text})
    window._pending_solicitudes.append(solicitud)
    helper_refresh_pending_ui_state(window)


def on_remove_pendiente(window: MainWindow) -> None:
    logger.info("CLICK eliminar_pendiente handler=_on_remove_pendiente")
    window._dump_estado_pendientes("click_eliminar_pendiente")
    selection = window.pendientes_table.selectionModel().selectedRows()
    if not selection:
        logger.info("_on_remove_pendiente early_return motivo=sin_seleccion")
        return
    logger.info("Se pide confirmación de borrado motivo=policy=always_confirm selection_count>0 (instrumentación)")
    confirm = QMessageBox.question(
        window,
        copy_text("solicitudes.confirm_delete_pending_title"),
        copy_text("solicitudes.confirm_delete_pending_message"),
    )
    if confirm != QMessageBox.StandardButton.Yes:
        return
    rows = sorted((index.row() for index in selection), reverse=True)
    ids_to_delete: list[int] = []
    for row in rows:
        if 0 <= row < len(window._pending_solicitudes):
            solicitud = window._pending_solicitudes[row]
            if solicitud.id is not None:
                ids_to_delete.append(solicitud.id)
    try:
        window._set_processing_state(True)
        for solicitud_id in ids_to_delete:
            with OperationContext("eliminar_pendiente") as operation:
                window._solicitud_use_cases.eliminar_solicitud(
                    solicitud_id, correlation_id=operation.correlation_id
                )
    except (ValidacionError, BusinessRuleError) as exc:
        window.toast.warning(str(exc), title="Validación")
        return
    except Exception as exc:  # pragma: no cover - fallback
        logger.exception("Error eliminando pendiente")
        window._show_critical_error(exc)
        return
    finally:
        window._set_processing_state(False)
    window._reload_pending_views()
    window._refresh_saldos()
    window.notifications.notify_operation(
        OperationFeedback(
            title="Pendientes eliminadas",
            happened="Las solicitudes pendientes seleccionadas se eliminaron.",
            affected_count=len(ids_to_delete),
            incidents="Sin incidencias.",
            next_step="Puedes añadir nuevas solicitudes o confirmar otras pendientes.",
        )
    )
