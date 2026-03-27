from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QDate, QItemSelectionModel, QTimer
from PySide6.QtWidgets import QAbstractItemView, QDialog, QMessageBox

from app.core.observability import OperationContext, log_event
from app.domain.services import BusinessRuleError, ValidacionError
from app.bootstrap.logging import log_operational_error
from app.ui.patterns import status_badge
from app.ui.notification_service import OperationFeedback
from app.ui.copy_catalog import copy_text
from app.ui.vistas.main_window import state_historico


logger = logging.getLogger(__name__)
_SETTINGS_HISTORICO_DELEGADA = "/".join(("historico", "delegada"))


def _range_is_inverted(date_from: Any, date_to: Any) -> bool:
    try:
        return bool(date_from > date_to)
    except TypeError:
        return False


def apply_historico_filters(window: Any) -> None:
    filtros = build_historico_filters(window)
    year_mode = filtros["year_mode"]
    date_from = filtros["date_from"]
    date_to = filtros["date_to"]

    if year_mode == "RANGE" and date_from.isValid() and date_to.isValid() and _range_is_inverted(date_from, date_to):
        # Para juniors: corregimos automáticamente para no bloquear al usuario ni colapsar la UI.
        date_from, date_to = date_to, date_from
        window.historico_desde_date.setDate(date_from)
        window.historico_hasta_date.setDate(date_to)
        QMessageBox.information(
            window,
            copy_text("ui.historico.rango_ajustado_titulo"),
            copy_text("ui.historico.rango_ajustado_mensaje"),
        )

    window.historico_proxy_model.set_filters(
        delegada_id=filtros["delegada_id"],
        ver_todas=filtros["ver_todas"],
        year_mode=year_mode,
        year=filtros["year"],
        month=filtros["month"],
        date_from=date_from,
        date_to=date_to,
    )
    window.historico_proxy_model.set_estado_code(window.historico_estado_combo.currentData())
    window._settings.setValue(_SETTINGS_HISTORICO_DELEGADA, filtros["delegada_id"])
    window._apply_historico_text_filter()
    window._update_historico_empty_state()


def build_historico_filters(window: Any) -> dict[str, Any]:
    year_mode, year, month = window._historico_period_filter_state()
    delegada_id = window.historico_delegada_combo.currentData()
    return {
        "year_mode": year_mode,
        "year": year,
        "month": month,
        "date_from": window.historico_desde_date.date(),
        "date_to": window.historico_hasta_date.date(),
        "delegada_id": delegada_id if isinstance(delegada_id, int) else None,
        "ver_todas": delegada_id is None,
    }


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


def _set_enabled_and_visible(widget: Any, enabled: bool, visible: bool) -> None:
    if widget is None:
        return
    set_enabled = getattr(widget, "setEnabled", None)
    if callable(set_enabled):
        set_enabled(enabled)
    set_visible = getattr(widget, "setVisible", None)
    if callable(set_visible):
        set_visible(visible)


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

    _set_enabled_and_visible(window.historico_periodo_anual_spin, anual_activo, anual_activo)
    _set_enabled_and_visible(window.historico_periodo_mes_ano_spin, mes_activo, mes_activo)
    _set_enabled_and_visible(window.historico_periodo_mes_combo, mes_activo, mes_activo)
    _set_enabled_and_visible(getattr(window, "historico_desde_label", None), rango_activo, rango_activo)
    _set_enabled_and_visible(window.historico_desde_date, rango_activo, rango_activo)
    _set_enabled_and_visible(getattr(window, "historico_hasta_label", None), rango_activo, rango_activo)
    _set_enabled_and_visible(window.historico_hasta_date, rango_activo, rango_activo)
    trigger_historico_filter_refresh(window)


def on_historico_filter_changed(window: Any, *_args: object, **_kwargs: object) -> None:
    trigger_historico_filter_refresh(window)


def on_historico_search_text_changed(window: Any, *_args: object, **_kwargs: object) -> None:
    timer = getattr(window, "_historico_filtro_timer", None)
    if timer is None:
        trigger_historico_filter_refresh(window)
        return
    timer.start(300)


def trigger_historico_filter_refresh(window: Any) -> None:
    QTimer.singleShot(0, window._apply_historico_filters)


def on_historico_apply_filters(window: Any) -> None:
    year_mode, year, month = window._historico_period_filter_state()
    delegada_id = window.historico_delegada_combo.currentData()
    logger.info(
        "UI_HISTORICO_APPLY_FILTERS todas=%s delegada_id=%s año=%s mes=%s desde=%s hasta=%s modo=%s",
        delegada_id is None,
        delegada_id,
        year,
        month,
        window.historico_desde_date.date().toString(copy_text("ui.formatos.qt_fecha_ymd")),
        window.historico_hasta_date.date().toString(copy_text("ui.formatos.qt_fecha_ymd")),
        year_mode,
    )
    window._apply_historico_filters()


def configure_historico_focus_order(window: Any) -> None:
    window.setTabOrder(window.historico_search_input, window.historico_estado_combo)
    window.setTabOrder(window.historico_estado_combo, window.historico_delegada_combo)
    window.setTabOrder(window.historico_delegada_combo, window.historico_desde_date)
    window.setTabOrder(window.historico_desde_date, window.historico_hasta_date)
    window.setTabOrder(window.historico_hasta_date, window.historico_table)


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
    return state_historico.obtener_solicitudes_historico_seleccionadas(window)


def selected_historico(window: Any) -> Any | None:
    return state_historico.obtener_solicitud_historico_seleccionada(window)


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
    state_historico.sincronizar_estado_seleccion_visible_historico(window)


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
        copy_text("ui.confirmaciones.no_visible_filtros"),
        copy_text("ui.historico.solicitud_confirmada_titulo"),
        copy_text("ui.historico.solicitud_confirmada_mensaje"),
    )


def on_export_historico_pdf(window: Any) -> None:
    export_handler = getattr(window, "_on_generar_pdf_historico", None)
    if callable(export_handler):
        export_handler()
        return
    logger.warning("export_historico_pdf_not_available")
    QMessageBox.information(
        window,
        copy_text("ui.historico.exportacion_titulo"),
        copy_text("ui.historico.funcion_no_disponible"),
    )


def on_generar_pdf_historico(window: Any) -> None:
    persona = window._current_persona()
    if persona is None:
        return
    selected = window._selected_historico_solicitudes()
    if not selected:
        window.toast.info(
            copy_text("ui.export_share.sin_registros"),
            title=copy_text("ui.historico.titulo"),
        )
        return
    try:
        default_name = window._servicio_destino_pdf_confirmacion.sugerir_nombre_pdf(selected)
    except (ValidacionError, BusinessRuleError) as exc:
        window.toast.warning(str(exc), title=copy_text("ui.historico.validacion_titulo"))
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
        window.toast.warning(str(exc), title=copy_text("ui.historico.validacion_titulo"))
        return
    except Exception as exc:  # pragma: no cover - fallback
        if isinstance(exc, OSError):
            log_operational_error(
                logger,
                copy_text("ui.historico.preview_export_error"),
                exc=exc,
                extra={"operation": "exportar_historico_pdf", "persona_id": persona.id or 0},
            )
        else:
            logger.exception("Error generando previsualización de PDF histórico")
        window._show_critical_error(exc)
        return
    if result == QDialog.DialogCode.Accepted:
        window._show_optional_notice(
            copy_text("ui.confirmaciones.export_pdf_ok"),
            copy_text("ui.historico.export_pdf_ok_titulo"),
            copy_text("ui.historico.export_pdf_ok_mensaje"),
        )


def on_open_historico_detalle(window: Any) -> None:
    solicitud = window._selected_historico()
    if solicitud is None:
        return
    estado = status_badge("CONFIRMED") if solicitud.generated else status_badge("PENDING")
    payload = {
        "ID": str(solicitud.id or "-"),
        copy_text("ui.historico.col_delegada"): window.historico_model.persona_name_for_id(solicitud.persona_id)
        or str(solicitud.persona_id),
        copy_text("ui.historico.col_fecha_solicitada"): solicitud.fecha_solicitud,
        copy_text("ui.historico.col_fecha_pedida"): solicitud.fecha_pedida,
        copy_text("ui.historico.col_desde"): solicitud.desde or "-",
        copy_text("ui.historico.col_hasta"): solicitud.hasta or "-",
        copy_text("ui.historico.col_completo"): "Sí" if solicitud.completo else "No",
        copy_text("ui.historico.col_horas"): str(solicitud.horas),
        copy_text("ui.historico.col_estado"): estado,
        copy_text("ui.historico.col_observaciones"): solicitud.observaciones or "",
        copy_text("ui.historico.col_notas"): solicitud.notas or "",
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
        window.toast.warning(str(exc), title=copy_text("ui.historico.validacion_titulo"))
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
            title=copy_text("ui.historico.eliminadas_titulo"),
            happened=copy_text("ui.historico.eliminadas_mensaje"),
            affected_count=len(ids_seleccionados),
            incidents=copy_text("ui.historico.sin_incidencias_titulo"),
            next_step=copy_text("ui.historico.sin_incidencias_mensaje"),
        )
    )
