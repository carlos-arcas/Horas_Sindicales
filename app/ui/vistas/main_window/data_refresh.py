from __future__ import annotations

import logging
try:
    from PySide6.QtCore import QTimer, Qt
except Exception:  # pragma: no cover
    QTimer = Qt = object

from app.domain.services import BusinessRuleError
from app.ui.toast_helpers import toast_error
from app.ui.vistas.main_window_helpers import build_historico_filters_payload, handle_historico_render_mismatch

logger = logging.getLogger(__name__)


def refresh_historico(window, *, force: bool = False) -> None:
    if window.historico_table is None or window.historico_model is None:
        logger.info("UI_HISTORICO_REFRESH_SKIPPED_NO_WIDGETS")
        return
    persona = window._current_persona()
    historico_filters = build_historico_filters_payload(
        delegada_id=window.historico_delegada_combo.currentData(),
        estado=window.historico_estado_combo.currentData(),
        desde=window.historico_desde_date.date().toString("yyyy-MM-dd"),
        hasta=window.historico_hasta_date.date().toString("yyyy-MM-dd"),
        search=window.historico_search_input.text().strip(),
        force=force,
        tab_index=window.main_tabs.currentIndex() if window.main_tabs is not None else None,
    )
    logger.info(
        "UI_HISTORICO_REFRESH_START persona_id=%s filtros=%s",
        persona.id if persona is not None else None,
        historico_filters,
    )
    solicitudes = window._solicitudes_controller.refresh_historico()
    solicitud_ids = [sol.id for sol in solicitudes if sol.id is not None]
    logger.info("UI_HISTORICO_QUERY_RESULT count=%s ids_first_5=%s", len(solicitudes), solicitud_ids[:5])

    table = window.historico_table
    model = window.historico_model
    proxy_model = window.historico_proxy_model

    previous_sorting_enabled = table.isSortingEnabled()
    table.setUpdatesEnabled(False)
    table.setSortingEnabled(False)
    try:
        if proxy_model.sourceModel() is not model:
            proxy_model.setSourceModel(model)
        model.set_solicitudes(solicitudes)
        window._apply_historico_filters()
        proxy_model.invalidateFilter()
        proxy_model.invalidate()
    finally:
        table.setSortingEnabled(previous_sorting_enabled)
        table.setUpdatesEnabled(True)

    QTimer.singleShot(0, lambda: table.sortByColumn(0, Qt.DescendingOrder))
    window._update_action_state()
    row_count = proxy_model.rowCount()
    logger.info("UI_HISTORICO_TABLE_RENDER row_count=%s", row_count)
    row_count = handle_historico_render_mismatch(
        solicitudes=solicitudes,
        row_count=row_count,
        table=table,
        model=model,
        proxy_model=proxy_model,
        apply_historico_filters=window._apply_historico_filters,
        toast_error_callback=lambda message: toast_error(window.toast, message),
    )
    if row_count == 0:
        logger.info("UI_HISTORICO_REFRESH_EMPTY")


def refresh_saldos(window) -> None:
    filtro = window._current_saldo_filtro()
    window._update_periodo_label()
    persona = window._current_persona()
    if persona is None:
        window._set_saldos_labels(None)
        return
    try:
        resumen = window._solicitud_use_cases.calcular_resumen_saldos(persona.id or 0, filtro)
    except BusinessRuleError as exc:
        window.toast.warning(str(exc), title="Validación")
        window._set_saldos_labels(None)
        return
    window._set_saldos_labels(resumen)


def reload_pending_views(window) -> None:
    persona = window._current_persona()
    window._pending_all_solicitudes = list(window._solicitud_use_cases.listar_pendientes_all())
    if window._pending_view_all:
        window._pending_solicitudes = list(window._pending_all_solicitudes)
    elif persona is None:
        window._pending_solicitudes = []
    else:
        window._pending_solicitudes = list(window._solicitud_use_cases.listar_pendientes_por_persona(persona.id or 0))

    pending_visible_ids = {solicitud.id for solicitud in window._pending_solicitudes if solicitud.id is not None}
    window._hidden_pendientes = [
        solicitud
        for solicitud in window._pending_all_solicitudes
        if solicitud.id is not None and solicitud.id not in pending_visible_ids
    ]
    hidden_count = len(window._hidden_pendientes)
    should_warn_hidden = hidden_count > 0 and not window._pending_view_all
    window.pending_filter_warning.setVisible(should_warn_hidden)
    window.revisar_ocultas_button.setVisible(should_warn_hidden)
    if should_warn_hidden:
        window.pending_filter_warning.setText(f"Hay pendientes en otras delegadas: {hidden_count}")
        window.revisar_ocultas_button.setText(f"Revisar pendientes ocultas ({hidden_count})")
        logger.warning(
            "Pendientes no visibles por filtro actual delegada_id=%s hidden=%s",
            persona.id if persona is not None else None,
            hidden_count,
        )
    else:
        window.pending_filter_warning.setText("")

    window._orphan_pendientes = list(window._solicitud_use_cases.listar_pendientes_huerfanas())
    window.huerfanas_model.set_solicitudes(window._orphan_pendientes)
    has_orphans = bool(window._orphan_pendientes)
    window.huerfanas_label.setVisible(has_orphans)
    window.huerfanas_table.setVisible(has_orphans)
    window.eliminar_huerfana_button.setVisible(has_orphans)

    if persona is not None:
        logger.info(
            "Cambio delegada id=%s pendientes_delegada=%s pendientes_totales=%s",
            persona.id,
            len(list(window._solicitud_use_cases.listar_pendientes_por_persona(persona.id or 0))),
            len(list(window._solicitud_use_cases.listar_pendientes_all())),
        )

    window._refresh_pending_ui_state()
