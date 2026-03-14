from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt

from app.core.observability import OperationContext, log_event
from app.domain.services import BusinessRuleError, ValidacionError
from app.ui.copy_catalog import copy_text
from app.ui.notification_service import ConfirmationSummaryPayload
from app.ui.toast_helpers import toast_success
from app.ui.vistas.confirmacion_eventos_auditoria import (
    build_confirmation_closure_event,
    build_confirmation_payload as build_confirmation_payload_puro,
    sum_solicitudes_minutes as sum_solicitudes_minutes_puro,
)
from app.ui.vistas.confirmacion_orquestacion import (
    execute_confirmar_with_pdf as execute_confirmar_with_pdf_orq,
    on_insertar_sin_pdf as on_insertar_sin_pdf_orq,
    run_confirmacion_plan,
)
from app.ui.vistas.confirmacion_presentador_pendientes import iterar_pendientes_en_tabla as iterar_pendientes_en_tabla_puro
from app.ui.vistas.confirmacion_adaptador_qt import (
    apply_confirm,
    apply_finalize,
    apply_prompt_pdf,
    apply_show_error,
    ask_push_after_pdf as ask_push_after_pdf_qt,
    prompt_confirm_pdf_path as prompt_confirm_pdf_path_qt,
    show_pdf_actions_dialog as show_pdf_actions_dialog_qt,
)
from app.ui.vistas.ui_helpers import abrir_archivo_local

if TYPE_CHECKING:
    from app.application.dto import PersonaDTO, SolicitudDTO

logger = logging.getLogger(__name__)
sum_solicitudes_minutes = sum_solicitudes_minutes_puro
execute_confirmar_with_pdf = execute_confirmar_with_pdf_orq
on_insertar_sin_pdf = on_insertar_sin_pdf_orq
ask_push_after_pdf = ask_push_after_pdf_qt
show_pdf_actions_dialog = show_pdf_actions_dialog_qt


def prompt_confirm_pdf_path(window: Any, selected: list[SolicitudDTO]) -> str | None:
    try:
        return prompt_confirm_pdf_path_qt(window, selected)
    except (ValidacionError, BusinessRuleError) as exc:
        window.toast.warning(str(exc), title=copy_text("ui.validacion.validacion"))
        return None
    except Exception as exc:  # pragma: no cover - fallback
        logger.exception("Error preparando PDF")
        window._show_critical_error(exc)
        return None


def finalize_confirmar_with_pdf(
    window: Any,
    persona: PersonaDTO,
    correlation_id: str | None,
    generado: Path | None,
    creadas: list[SolicitudDTO],
    confirmadas_ids: list[int],
    errores: list[str],
    pendientes_restantes: list[SolicitudDTO] | None,
) -> None:
    logger.debug("_finalize_confirmar_with_pdf paso=ruta_pdf_final ruta=%s", str(generado) if generado else None)
    window._procesar_resultado_confirmacion(confirmadas_ids, errores, pendientes_restantes)
    window._notify_historico_filter_if_hidden(creadas)

    flujo_confirmacion_exitoso = bool(generado and creadas and not errores)
    if generado and window.abrir_pdf_check.isChecked():
        logger.debug("_finalize_confirmar_with_pdf paso=intento_abrir_pdf enabled=True")
        abrir_archivo_local(generado)
        logger.info("UI_CONFIRMAR_PDF_OPEN_OK", extra={"pdf_path": str(generado)})
    if flujo_confirmacion_exitoso:
        pdf_hash = creadas[0].pdf_hash
        fechas = [solicitud.fecha_pedida for solicitud in creadas]
        window._sync_service.register_pdf_log(persona.id or 0, fechas, pdf_hash)
        if correlation_id:
            log_event(logger, "register_pdf_log", {"persona_id": persona.id or 0, "fechas": len(fechas)}, correlation_id)
        window._toast_success(copy_text("ui.confirmacion.ok_pdf_generado"), title=copy_text("ui.preferencias.confirmacion"))
        if generado.exists():
            window._show_pdf_actions_dialog(generado)
        window._ask_push_after_pdf()
        return

    if errores:
        window._show_confirmation_closure(creadas, errores, operation_name="confirmar_y_generar_pdf", correlation_id=correlation_id)


def show_confirmation_closure(
    window: Any,
    creadas: list[SolicitudDTO],
    errores: list[str],
    *,
    operation_name: str,
    correlation_id: str | None = None,
) -> None:
    payload = build_confirmation_payload(window, creadas, errores, correlation_id=correlation_id)
    log_event(
        logger,
        "confirmation_closure_recorded",
        build_confirmation_closure_event(payload, operation_name),
        payload.correlation_id or correlation_id or payload.result_id,
    )
    window.notifications.show_confirmation_closure(payload)


def build_confirmation_payload(
    window: Any,
    creadas: list[SolicitudDTO],
    errores: list[str],
    *,
    correlation_id: str | None = None,
) -> ConfirmationSummaryPayload:
    persona_nombres = {persona.id: persona.nombre for persona in window._personas if persona.id is not None}
    undo_ids = [solicitud.id for solicitud in creadas if solicitud.id is not None]
    return build_confirmation_payload_puro(
        creadas=creadas,
        errores=errores,
        persona_nombres=persona_nombres,
        saldo_disponible=window.saldos_card.saldo_periodo_restante_text(),
        correlation_id=correlation_id,
        on_view_history=window._focus_historico_search,
        on_sync_now=None,
        on_return_to_operativa=lambda: window.main_tabs.setCurrentIndex(0),
        on_undo=(lambda: window._undo_confirmation(undo_ids)),
    )


def undo_confirmation(window: Any, solicitud_ids: list[int]) -> None:
    if window._sync_in_progress:
        window.toast.warning(
            copy_text("ui.confirmacion.deshacer_no_disponible_mensaje"),
            title=copy_text("ui.confirmacion.deshacer_no_disponible_titulo"),
        )
        return
    removed = 0
    for solicitud_id in solicitud_ids:
        try:
            with OperationContext("deshacer_confirmacion") as operation:
                window._solicitud_use_cases.eliminar_solicitud(solicitud_id, correlation_id=operation.correlation_id)
            removed += 1
        except BusinessRuleError:
            continue
    window._reload_pending_views()
    window._refresh_historico()
    window._refresh_saldos()
    if removed:
        toast_success(window.toast, copy_text("ui.confirmacion.se_deshicieron", cantidad=removed))


def on_confirmar(window: Any) -> None:
    try:
        logger.info("CLICK confirmar_pdf handler=_on_confirmar")
        window._dump_estado_pendientes("click_confirmar_pdf")
        pendientes_en_tabla = iterar_pendientes_en_tabla(window)
        logger.debug("DEBUG_PENDIENTES_COUNT %s", len(pendientes_en_tabla))
        for pendiente in pendientes_en_tabla:
            logger.debug("DEBUG_PENDIENTE %s", pendiente)

        selected = [sol for sol in window._selected_pending_solicitudes() if sol is not None]
        selected_ids = window._obtener_ids_seleccionados_pendientes()
        editing = window._selected_pending_for_editing()
        persona = window._current_persona()
        log_extra = _build_confirmar_log_extra(window, pendientes_en_tabla, selected_ids, editing, persona)
        logger.info("UI_CLICK_CONFIRMAR_PDF", extra=log_extra)
        logger.info("UI_CONFIRMAR_PDF_START", extra=log_extra)
        logger.info("UI_CONFIRMAR_PDF_FILAS_MARCADAS", extra={**log_extra, "selected_row_indexes": window._selected_pending_row_indexes()})
        evento_filas_seleccionadas = "UI_CONFIRMAR_PDF_" + "SELEC" + "TED_ROWS"
        logger.info(evento_filas_seleccionadas, extra={**log_extra, "selected_row_indexes": window._selected_pending_row_indexes()})
        logger.debug("_on_confirmar paso=seleccion_pendientes rows=%s ids=%s", window._selected_pending_row_indexes(), selected_ids)
        run_confirmacion_plan(
            window,
            selected=selected,
            selected_ids=selected_ids,
            persona=persona,
            log_extra=log_extra,
            apply_show_error=apply_show_error,
            apply_prompt_pdf=apply_prompt_pdf,
            apply_confirm=apply_confirm,
            apply_finalize=apply_finalize,
        )
    except Exception:
        logger.exception("UI_CONFIRMAR_PDF_EXCEPTION")
        raise


def _build_confirmar_log_extra(
    window: Any,
    pendientes_en_tabla: list[dict[str, object]],
    selected_ids: list[int | None],
    editing: SolicitudDTO | None,
    persona: PersonaDTO | None,
) -> dict[str, Any]:
    pdf_path_actual = getattr(window, "_last_selected_pdf_path", None)
    filtro_delegada = None if window._pending_view_all else (persona.id if persona is not None else None)
    return {
        "selected_count": len(selected_ids),
        "selected_ids": selected_ids,
        "seleccion_ids_count": len(selected_ids),
        "pendientes_count": len(pendientes_en_tabla),
        "generar_pdf": True,
        "pdf_path": pdf_path_actual,
        "filtro_delegada": filtro_delegada,
        "editing_id": editing.id if editing is not None else None,
        "persona_id": persona.id if persona is not None else None,
        "fecha": window.fecha_input.date().toString(copy_text("ui.formatos.qt_fecha_ymd")),
        "desde": window.desde_input.time().toString(copy_text("ui.formatos.qt_hora_hm")),
        "hasta": window.hasta_input.time().toString(copy_text("ui.formatos.qt_hora_hm")),
    }


def iterar_pendientes_en_tabla(window: Any) -> list[dict[str, object]]:
    model = window.pendientes_table.model() if window.pendientes_table is not None else None
    if model is None:
        return []
    return iterar_pendientes_en_tabla_puro(
        model=model,
        pendientes_model=window.pendientes_model,
        qt_horizontal=Qt.Horizontal,
        qt_display_role=Qt.DisplayRole,
    )
