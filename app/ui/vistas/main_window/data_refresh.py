from __future__ import annotations

import logging
try:
    from PySide6.QtCore import QTimer, Qt
except Exception:  # pragma: no cover
    QTimer = Qt = object

from app.domain.services import BusinessRuleError
from app.ui.copy_catalog import copy_text
from app.ui.toast_helpers import toast_error
from app.ui.vistas.main_window_helpers import build_historico_filters_payload, handle_historico_render_mismatch
from app.ui.vistas.main_window.estado_dataset_pendientes import calcular_estado_dataset_pendientes
from app.ui.vistas.presentacion_pendientes import construir_estado_vista_pendientes

logger = logging.getLogger(__name__)


def refresh_historico(window, *, force: bool = False) -> None:
    if window.historico_table is None or window.historico_model is None:
        logger.info("UI_HISTORICO_REFRESH_SKIPPED_NO_WIDGETS")
        return
    persona = window._current_persona()
    historico_filters = build_historico_filters_payload(
        delegada_id=window.historico_delegada_combo.currentData(),
        estado=window.historico_estado_combo.currentData(),
        desde=window.historico_desde_date.date().toString(copy_text("ui.formatos.qt_fecha_ymd")),
        hasta=window.historico_hasta_date.date().toString(copy_text("ui.formatos.qt_fecha_ymd")),
        search=window.historico_search_input.text().strip(),
        force=force,
        tab_index=window.main_tabs.currentIndex() if window.main_tabs is not None else None,
    )
    logger.info(
        "UI_HISTORICO_REFRESH_START action=historico_refresh reason_code=user_or_system_refresh persona_id=%s filtros=%s",
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
    if hasattr(window, "_historico_ids_seleccionados"):
        window._historico_ids_seleccionados = set()
    if getattr(window, "eliminar_button", None) is not None:
        window.eliminar_button.setText(copy_text("ui.historico.eliminar_boton").format(n=0))
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
        window.toast.warning(str(exc), title=copy_text("ui.data_refresh.validacion_titulo"))
        window._set_saldos_labels(None)
        return
    window._set_saldos_labels(resumen)


def reload_pending_views(window) -> None:
    persona = window._current_persona()
    delegada_activa_id = persona.id if persona is not None else None
    logger.info(
        "UI_PENDIENTES_RELOAD_START",
        extra={
            "pending_view_all": bool(window._pending_view_all),
            "persona_id": delegada_activa_id,
            "hidden_previas": len(window._hidden_pendientes),
            "otras_delegadas_previas": len(getattr(window, "_pending_otras_delegadas", [])),
            "huerfanas_previas": len(window._orphan_pendientes),
            "pendientes_visibles_previas": len(window._pending_solicitudes),
            "pendientes_totales_previas": len(window._pending_all_solicitudes),
        },
    )
    pendientes_totales = list(window._solicitud_use_cases.listar_pendientes_all())
    estado_dataset = calcular_estado_dataset_pendientes(
        pendientes_totales=pendientes_totales,
        delegada_activa_id=delegada_activa_id,
        ver_todas_delegadas=bool(window._pending_view_all),
    )
    window._pending_all_solicitudes = estado_dataset.pendientes_totales
    window._pending_solicitudes = estado_dataset.pendientes_visibles
    window._hidden_pendientes = estado_dataset.pendientes_ocultas
    window._pending_otras_delegadas = estado_dataset.pendientes_otras_delegadas

    estado_vista = construir_estado_vista_pendientes(
        estado_dataset=estado_dataset,
        ver_todas_delegadas=bool(window._pending_view_all),
    )
    hidden_count = len(window._hidden_pendientes)
    other_delegadas_count = len(window._pending_otras_delegadas)
    window.pending_filter_warning.setVisible(estado_vista.warning_visible)
    window.pending_filter_warning.setText(estado_vista.warning_text)
    window.revisar_ocultas_button.setVisible(estado_vista.revisar_visible)
    window.revisar_ocultas_button.setText(estado_vista.revisar_text)
    if estado_vista.warning_visible:
        logger.warning(
            "Pendientes no visibles por filtro actual delegada_id=%s hidden=%s other_delegadas=%s",
            delegada_activa_id,
            hidden_count,
            other_delegadas_count,
        )

    if estado_dataset.motivos_exclusion:
        logger.info(
            "UI_PENDIENTES_EXCLUSION_MOTIVOS",
            extra={
                "pending_view_all": bool(window._pending_view_all),
                "persona_id": delegada_activa_id,
                "motivos_exclusion": estado_dataset.motivos_exclusion,
            },
        )

    window._orphan_pendientes = list(window._solicitud_use_cases.listar_pendientes_huerfanas())
    window.huerfanas_model.set_solicitudes(window._orphan_pendientes)
    has_orphans = bool(window._orphan_pendientes)
    logger.info(
        "UI_PENDIENTES_RECALC",
        extra={
            "pending_view_all": bool(window._pending_view_all),
            "pendientes_visibles": len(window._pending_solicitudes),
            "pendientes_totales": len(window._pending_all_solicitudes),
            "hidden_count": len(window._hidden_pendientes),
            "other_delegadas_count": len(window._pending_otras_delegadas),
            "huerfanas_count": len(window._orphan_pendientes),
        },
    )
    window.huerfanas_label.setVisible(has_orphans)
    window.huerfanas_table.setVisible(has_orphans)
    window.eliminar_huerfana_button.setVisible(has_orphans)

    if persona is not None:
        logger.info(
            "Cambio delegada id=%s pendientes_delegada=%s pendientes_totales=%s",
            persona.id,
            len(window._pending_solicitudes),
            len(list(window._solicitud_use_cases.listar_pendientes_all())),
        )

    window._pending_selection_anchor_row = None
    window._refresh_pending_ui_state()
