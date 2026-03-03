from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QDate, QItemSelectionModel
from PySide6.QtWidgets import QAbstractItemView, QDialog, QMessageBox

from app.core.observability import OperationContext, log_event
from app.domain.services import BusinessRuleError, ValidacionError
from app.bootstrap.logging import log_operational_error
from app.ui.patterns import status_badge
from app.ui.notification_service import OperationFeedback
from app.ui.copy_catalog import copy_text


logger = logging.getLogger(__name__)


def apply_historico_filters(window: Any) -> None:
    year_mode, year, month = window._historico_period_filter_state()
    ver_todas = window.historico_todas_delegadas_check.isChecked()
    delegada_id = None if ver_todas else window.historico_delegada_combo.currentData()
    date_from = window.historico_desde_date.date()
    date_to = window.historico_hasta_date.date()

    if year_mode == "RANGE" and date_from.isValid() and date_to.isValid() and date_from > date_to:
        # Para juniors: corregimos automáticamente para no bloquear al usuario ni colapsar la UI.
        date_from, date_to = date_to, date_from
        window.historico_desde_date.setDate(date_from)
        window.historico_hasta_date.setDate(date_to)
        QMessageBox.information(
            window,
            "Rango ajustado",
            "La fecha 'Desde' era posterior a 'Hasta'. Se corrigió automáticamente el rango.",
        )

    window.historico_proxy_model.set_filters(
        delegada_id=delegada_id,
        ver_todas=ver_todas,
        year_mode=year_mode,
        year=year,
        month=month,
        date_from=date_from,
        date_to=date_to,
    )
    window.historico_proxy_model.set_estado_code(window.historico_estado_combo.currentData())
    window._settings.setValue("historico/delegada", delegada_id)
    window._apply_historico_text_filter()
    window._update_historico_empty_state()


def apply_historico_default_range(window: Any) -> None:
    today = QDate.currentDate()
    window.historico_desde_date.setDate(today.addDays(-30))
    window.historico_hasta_date.setDate(today)

    if getattr(window, "historico_periodo_rango_radio", None) is not None:
        window.historico_periodo_rango_radio.setChecked(True)

    apply_filters = getattr(window, "_apply_historico_filters", None)
    if callable(apply_filters) and getattr(window, "historico_proxy_model", None) is not None:
        apply_filters()


def apply_historico_last_30_days(window: Any) -> None:
    window.historico_desde_date.setDate(QDate.currentDate().addDays(-30))
    window.historico_hasta_date.setDate(QDate.currentDate())
    window._apply_historico_filters()


def on_historico_periodo_mode_changed(
    window: Any,
    mode: str | bool | None = None,
    *_args: object,
    **_kwargs: object,
) -> None:
    if isinstance(mode, str):
        window.historico_periodo_anual_radio.setChecked(mode == "ALL_YEAR")
        window.historico_periodo_mes_radio.setChecked(mode == "YEAR_MONTH")
        window.historico_periodo_rango_radio.setChecked(mode == "RANGE")

    anual_activo = window.historico_periodo_anual_radio.isChecked()
    mes_activo = window.historico_periodo_mes_radio.isChecked()
    rango_activo = window.historico_periodo_rango_radio.isChecked()

    window.historico_periodo_anual_spin.setEnabled(anual_activo)
    window.historico_periodo_mes_ano_spin.setEnabled(mes_activo)
    window.historico_periodo_mes_combo.setEnabled(mes_activo)
    window.historico_desde_date.setEnabled(rango_activo)
    window.historico_hasta_date.setEnabled(rango_activo)
    window._apply_historico_filters()


def on_historico_apply_filters(window: Any) -> None:
    year_mode, year, month = window._historico_period_filter_state()
    delegada_id = None if window.historico_todas_delegadas_check.isChecked() else window.historico_delegada_combo.currentData()
    logger.info(
        "UI_HISTORICO_APPLY_FILTERS todas=%s delegada_id=%s año=%s mes=%s desde=%s hasta=%s modo=%s",
        window.historico_todas_delegadas_check.isChecked(),
        delegada_id,
        year,
        month,
        window.historico_desde_date.date().toString("yyyy-MM-dd"),
        window.historico_hasta_date.date().toString("yyyy-MM-dd"),
        year_mode,
    )
    window._apply_historico_filters()


def configure_historico_focus_order(window: Any) -> None:
    window.setTabOrder(window.historico_search_input, window.historico_estado_combo)
    window.setTabOrder(window.historico_estado_combo, window.historico_delegada_combo)
    window.setTabOrder(window.historico_delegada_combo, window.historico_desde_date)
    window.setTabOrder(window.historico_desde_date, window.historico_hasta_date)
    window.setTabOrder(window.historico_hasta_date, window.historico_apply_filters_button)
    window.setTabOrder(window.historico_apply_filters_button, window.historico_table)


def focus_historico_search(window: Any) -> None:
    window.historico_search_input.setFocus()
    window.historico_search_input.selectAll()


def apply_historico_text_filter(window: Any) -> None:
    window.historico_proxy_model.set_search_text(window.historico_search_input.text())
    window._update_action_state()


def historico_period_filter_state(window: Any) -> tuple[str, int | None, int | None]:
    if window.historico_periodo_anual_radio.isChecked():
        return "ALL_YEAR", window.historico_periodo_anual_spin.value(), None
    if window.historico_periodo_mes_radio.isChecked():
        return "YEAR_MONTH", window.historico_periodo_mes_ano_spin.value(), window.historico_periodo_mes_combo.currentData()
    return "RANGE", None, None


def update_historico_empty_state(window: Any) -> None:
    has_rows = window.historico_proxy_model.rowCount() > 0
    window.historico_empty_state.setVisible(not has_rows)
    window.historico_details_content.setVisible(True)


def on_historico_escape(window: Any) -> None:
    if window.historico_search_input.hasFocus():
        window.historico_search_input.clearFocus()
        return
    window.historico_table.clearSelection()


def selected_historico_solicitudes(window: Any) -> list[Any]:
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


def selected_historico(window: Any) -> Any | None:
    selected = window._selected_historico_solicitudes()
    return selected[0] if selected else None


def on_historico_select_all_visible_toggled(window: Any, checked: bool) -> None:
    selection_model = window.historico_table.selectionModel()
    if selection_model is None:
        return
    flag = QItemSelectionModel.SelectionFlag.Select if checked else QItemSelectionModel.SelectionFlag.Deselect
    for row in range(window.historico_proxy_model.rowCount()):
        index = window.historico_proxy_model.index(row, 0)
        selection_model.select(index, flag | QItemSelectionModel.SelectionFlag.Rows)
    window._update_action_state()


def sync_historico_select_all_visible_state(window: Any) -> None:
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


def focus_historico_duplicate(window: Any, solicitud: Any) -> None:
    window._refresh_historico()
    for row in range(window.historico_model.rowCount()):
        model_solicitud = window.historico_model.solicitud_at(row)
        if model_solicitud.id == solicitud.id:
            source_index = window.historico_model.index(row, 0)
            proxy_index = window.historico_proxy_model.mapFromSource(source_index)
            if proxy_index.isValid():
                window.historico_table.clearSelection()
                window.historico_table.selectRow(proxy_index.row())
                window.historico_table.scrollTo(
                    proxy_index,
                    QAbstractItemView.ScrollHint.PositionAtCenter,
                )
            break


def notify_historico_filter_if_hidden(window: Any, solicitudes_insertadas: list[Any]) -> None:
    inserted_ids = {solicitud.id for solicitud in solicitudes_insertadas if solicitud.id is not None}
    if not inserted_ids:
        return
    visibles_ids: set[int] = set()
    for row in range(window.historico_proxy_model.rowCount()):
        proxy_index = window.historico_proxy_model.index(row, 0)
        source_index = window.historico_proxy_model.mapToSource(proxy_index)
        solicitud = window.historico_model.solicitud_at(source_index.row())
        if solicitud and solicitud.id is not None:
            visibles_ids.add(solicitud.id)
    if inserted_ids.issubset(visibles_ids):
        return
    logger.info(
        "Solicitudes insertadas en histórico pero no visibles por filtros actuales: ids=%s",
        sorted(inserted_ids - visibles_ids),
    )
    window._show_optional_notice(
        "confirmaciones/no_visible_filtros",
        "Solicitud confirmada",
        "Solicitud confirmada. Ajusta filtros para verla en Histórico.",
    )


def on_export_historico_pdf(window: Any) -> None:
    export_handler = getattr(window, "_on_generar_pdf_historico", None)
    if callable(export_handler):
        export_handler()
        return
    logger.warning("export_historico_pdf_not_available")
    QMessageBox.information(window, "Exportación", "Función no disponible")


def on_generar_pdf_historico(window: Any) -> None:
    persona = window._current_persona()
    if persona is None:
        return
    selected = window._selected_historico_solicitudes()
    if not selected:
        window.toast.info("No hay solicitudes para exportar.", title="Histórico")
        return
    try:
        default_name = window._solicitud_use_cases.sugerir_nombre_pdf(selected)
    except (ValidacionError, BusinessRuleError) as exc:
        window.toast.warning(str(exc), title="Validación")
        return
    except Exception as exc:  # pragma: no cover - fallback
        logger.exception("Error preparando PDF histórico")
        window._show_critical_error(exc)
        return

    def _generate_preview(target: Path) -> Path:
        with OperationContext("exportar_historico_pdf") as operation:
            log_event(
                logger,
                "exportar_historico_pdf_started",
                {"persona_id": persona.id or 0, "count": len(selected)},
                operation.correlation_id,
            )
            pdf = window._solicitud_use_cases.generar_pdf_historico(
                selected, target, correlation_id=operation.correlation_id
            )
            log_event(logger, "exportar_historico_pdf_finished", {"path": str(pdf)}, operation.correlation_id)
            return pdf

    try:
        preview = window._pdf_preview_dialog_class(_generate_preview, default_name, window)
        result = preview.exec()
    except (ValidacionError, BusinessRuleError) as exc:
        window.toast.warning(str(exc), title="Validación")
        return
    except Exception as exc:  # pragma: no cover - fallback
        if isinstance(exc, OSError):
            log_operational_error(
                logger,
                "File export failed during PDF preview",
                exc=exc,
                extra={"operation": "exportar_historico_pdf", "persona_id": persona.id or 0},
            )
        else:
            logger.exception("Error generando previsualización de PDF histórico")
        window._show_critical_error(exc)
        return
    if result == QDialog.DialogCode.Accepted:
        window._show_optional_notice(
            "confirmaciones/export_pdf_ok",
            "Exportación",
            "Exportación PDF OK",
        )


def on_open_historico_detalle(window: Any) -> None:
    solicitud = window._selected_historico()
    if solicitud is None:
        return
    estado = status_badge("CONFIRMED") if solicitud.generated else status_badge("PENDING")
    payload = {
        "ID": str(solicitud.id or "-"),
        "Delegada": window.historico_model.persona_name_for_id(solicitud.persona_id) or str(solicitud.persona_id),
        "Fecha solicitada": solicitud.fecha_solicitud,
        "Fecha pedida": solicitud.fecha_pedida,
        "Desde": solicitud.desde or "-",
        "Hasta": solicitud.hasta or "-",
        "Completo": "Sí" if solicitud.completo else "No",
        "Horas": str(solicitud.horas),
        "Estado": estado,
        "Observaciones": solicitud.observaciones or "",
        "Notas": solicitud.notas or "",
    }
    dialog = window._historico_detalle_dialog_class(payload, window)
    dialog.exec()


def on_eliminar(window: Any) -> None:
    ids_seleccionados = set(getattr(window, "_historico_ids_seleccionados", set()))
    logger.info("CLICK eliminar_historico handler=_on_eliminar selected=%s", len(ids_seleccionados))
    if not ids_seleccionados:
        logger.info("_on_eliminar early_return motivo=sin_seleccion")
        return
    try:
        window._set_processing_state(True)
        for solicitud_id in sorted(ids_seleccionados):
            with OperationContext("eliminar_solicitud") as operation:
                window._solicitud_use_cases.eliminar_solicitud(
                    solicitud_id, correlation_id=operation.correlation_id
                )
    except (ValidacionError, BusinessRuleError) as exc:
        window.toast.warning(str(exc), title="Validación")
        return
    except Exception as exc:  # pragma: no cover - fallback
        logger.exception("Error eliminando solicitud")
        window._show_critical_error(exc)
        return
    finally:
        window._set_processing_state(False)
    window._historico_ids_seleccionados = set()
    clear_selection = getattr(window.historico_table, "clearSelection", None)
    if callable(clear_selection):
        clear_selection()
    window._refresh_historico()
    window._refresh_saldos()
    window.eliminar_button.setText(copy_text("ui.historico.eliminar_boton").format(n=0))
    window._update_action_state()
    window.notifications.notify_operation(
        OperationFeedback(
            title="Solicitudes eliminadas",
            happened="Las solicitudes seleccionadas se eliminaron del histórico.",
            affected_count=len(ids_seleccionados),
            incidents="Sin incidencias.",
            next_step="Puedes continuar o revisar histórico.",
        )
    )
