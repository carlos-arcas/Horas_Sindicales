from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDialog

from app.core.observability import OperationContext, log_event
from app.domain.services import BusinessRuleError, ValidacionError
from app.bootstrap.logging import log_operational_error
from app.ui.patterns import status_badge

if TYPE_CHECKING:
    from app.application.dto import SolicitudDTO


logger = logging.getLogger(__name__)


def apply_historico_filters(window: Any) -> None:
    year_mode, year, month = window._historico_period_filter_state()
    ver_todas = window.historico_todas_delegadas_check.isChecked()
    delegada_id = None if ver_todas else window.historico_delegada_combo.currentData()
    window.historico_proxy_model.set_filters(
        delegada_id=delegada_id,
        ver_todas=ver_todas,
        year_mode=year_mode,
        year=year,
        month=month,
        date_from=window.historico_desde_date.date(),
        date_to=window.historico_hasta_date.date(),
    )
    window.historico_proxy_model.set_estado_code(window.historico_estado_combo.currentData())
    window._settings.setValue("historico/delegada", delegada_id)
    window._apply_historico_text_filter()
    window._update_historico_empty_state()


def apply_historico_default_range(window: Any) -> None:
    window.historico_desde_date.setDate(QDate.currentDate().addDays(-30))
    window.historico_hasta_date.setDate(QDate.currentDate())


def apply_historico_last_30_days(window: Any) -> None:
    window.historico_desde_date.setDate(QDate.currentDate().addDays(-30))
    window.historico_hasta_date.setDate(QDate.currentDate())
    window._apply_historico_filters()


def on_historico_periodo_mode_changed(window: Any) -> None:
    anual_activo = window.historico_periodo_anual_radio.isChecked()
    mes_activo = window.historico_periodo_mes_radio.isChecked()
    rango_activo = window.historico_periodo_rango_radio.isChecked()

    window.historico_periodo_anual_spin.setEnabled(anual_activo)
    window.historico_periodo_mes_ano_spin.setEnabled(mes_activo)
    window.historico_periodo_mes_combo.setEnabled(mes_activo)
    window.historico_desde_date.setEnabled(rango_activo)
    window.historico_hasta_date.setEnabled(rango_activo)


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


def clear_historico_filters(window: Any) -> None:
    logger.info("UI_HISTORICO_CLEAR_FILTERS")
    window.historico_todas_delegadas_check.setChecked(True)
    window.historico_delegada_combo.setCurrentIndex(0)
    window.historico_periodo_rango_radio.setChecked(True)
    window.historico_periodo_anual_spin.setValue(QDate.currentDate().year())
    window.historico_periodo_mes_ano_spin.setValue(QDate.currentDate().year())
    window.historico_periodo_mes_combo.setCurrentIndex(QDate.currentDate().month() - 1)
    window._apply_historico_default_range()
    window._on_historico_periodo_mode_changed()
    window._apply_historico_filters()


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


def on_resync_historico(window: Any) -> None:
    selected_count = len(window._selected_historico_solicitudes())
    if selected_count == 0:
        return
    window.toast.info(
        f"Re-sincronización preparada para {selected_count} solicitud(es). Ejecuta Sincronizar para completar.",
        title="Histórico",
    )
