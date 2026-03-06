from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, TypeAlias

from app.application.use_cases.confirmacion_pdf.modelos import SolicitudConfirmarPdfPeticion
from app.application.use_cases.solicitudes.validaciones import validar_seleccion_confirmacion
from app.bootstrap.logging import log_operational_error
from app.core.observability import OperationContext, log_event
from app.ui.copy_catalog import copy_text
from app.ui.vistas.confirmacion_eventos_auditoria import (
    build_confirmar_pdf_finished_event,
    build_confirmar_pdf_started_event,
)
from app.ui.vistas.confirmacion_presenter import ConfirmacionEntrada, plan_confirmacion
from app.ui.vistas.confirmacion_presentador_pendientes import (
    calcular_filtro_delegada_para_confirmacion,
    contar_pendientes_restantes,
    filtrar_pendientes_restantes,
    seleccionar_creadas_por_ids,
)

# Evitamos imports de DTOs solo de tipado en runtime para no introducir
# cargas/ciclos durante el arranque de la UI.
if TYPE_CHECKING:
    from app.application.dto import PersonaDTO, SolicitudDTO

logger = logging.getLogger(__name__)
ResultadoConfirmacionPdf: TypeAlias = tuple[
    str | None,
    Path | None,
    list["SolicitudDTO"],
    list[int],
    list[str],
    list["SolicitudDTO"] | None,
]


def execute_confirmar_with_pdf(window: Any, persona: PersonaDTO, selected: list[SolicitudDTO], pdf_path: str) -> ResultadoConfirmacionPdf | None:
    correlation_id: str | None = None
    try:
        window._set_processing_state(True)
        with OperationContext("confirmar_y_generar_pdf") as operation:
            correlation_id = operation.correlation_id
            log_event(
                logger,
                "confirmar_y_generar_pdf_started",
                build_confirmar_pdf_started_event(selected, pdf_path),
                operation.correlation_id,
            )
            confirmadas_ids, errores, generado, creadas, pendientes_restantes = _confirmar_lote(window, persona, selected, pdf_path, operation.correlation_id)
            log_event(
                logger,
                "confirmar_y_generar_pdf_finished",
                build_confirmar_pdf_finished_event(
                    creadas=creadas,
                    confirmadas_ids=confirmadas_ids,
                    errores=errores,
                    pendientes_restantes_count=contar_pendientes_restantes(pendientes_restantes),
                    pdf_generado=bool(generado),
                ),
                operation.correlation_id,
            )
            return correlation_id, generado, creadas, confirmadas_ids, errores, pendientes_restantes
    except Exception as exc:  # pragma: no cover - fallback
        _manejar_error_confirmar_pdf(window, persona, correlation_id, exc)
        return None
    finally:
        window._set_processing_state(False)


def _confirmar_lote(
    window: Any,
    persona: PersonaDTO,
    selected: list[SolicitudDTO],
    pdf_path: str,
    correlation_id: str,
) -> tuple[list[int], list[str], Path | None, list[SolicitudDTO], list[SolicitudDTO] | None]:
    caso_uso = getattr(window, "_confirmar_pendientes_pdf_caso_uso", None)
    if caso_uso is None:
        filtro_delegada = calcular_filtro_delegada_para_confirmacion(window._pending_view_all, persona.id)
        return window._solicitudes_controller.confirmar_lote(
            selected,
            correlation_id=correlation_id,
            generar_pdf=True,
            pdf_path=pdf_path,
            filtro_delegada=filtro_delegada,
        )
    request = SolicitudConfirmarPdfPeticion(
        pendientes_ids=[solicitud.id for solicitud in selected if solicitud.id is not None],
        generar_pdf=True,
        destino_pdf=Path(pdf_path),
        correlation_id=correlation_id,
    )
    result = caso_uso(request)
    creadas = seleccionar_creadas_por_ids(selected, result.confirmadas_ids)
    pendientes_restantes = filtrar_pendientes_restantes(window._pending_all_solicitudes, result.pendientes_restantes)
    return result.confirmadas_ids, result.errores, result.ruta_pdf, creadas, pendientes_restantes


def _manejar_error_confirmar_pdf(window: Any, persona: PersonaDTO, correlation_id: str | None, exc: Exception) -> None:
    if isinstance(exc, OSError):
        log_operational_error(
            logger,
            "ui.confirmacion.file_export_failed_during_confirm_pdf",
            exc=exc,
            extra={"operation": "confirmar_y_generar_pdf", "persona_id": persona.id or 0, "correlation_id": correlation_id},
        )
    else:
        logger.exception("Error confirmando solicitudes")
    window._show_critical_error(exc)


def on_insertar_sin_pdf(window: Any) -> None:
    logger.info("CLICK confirmar_sin_pdf handler=_on_insertar_sin_pdf")
    window._dump_estado_pendientes("click_confirmar_sin_pdf")
    if not window._run_preconfirm_checks():
        logger.info("_on_insertar_sin_pdf early_return motivo=preconfirm_checks")
        return
    persona = window._current_persona()
    selected = window._selected_pending_solicitudes()
    if persona is None:
        logger.info("_on_insertar_sin_pdf early_return motivo=no_persona")
        return
    warning_message = validar_seleccion_confirmacion(len(selected))
    if warning_message:
        window.toast.warning(warning_message, title=copy_text("ui.confirmacion.seleccion_requerida"))
        logger.info("_on_insertar_sin_pdf early_return motivo=sin_seleccion")
        return
    if window._pending_conflict_rows:
        logger.info("_on_insertar_sin_pdf early_return motivo=conflictos_pendientes")
        window.toast.warning(
            copy_text("ui.confirmacion.conflictos_detectados_mensaje"),
            title=copy_text("ui.confirmacion.conflictos_detectados_titulo"),
        )
        return
    _confirmar_sin_pdf(window, selected)


def _confirmar_sin_pdf(window: Any, selected: list[SolicitudDTO]) -> None:
    try:
        window._set_processing_state(True)
        with OperationContext("confirmar_sin_pdf") as operation:
            log_event(logger, "confirmar_sin_pdf_started", {"count": len(selected)}, operation.correlation_id)
            confirmadas_ids, errores, _ruta, creadas, pendientes_restantes = window._solicitudes_controller.confirmar_lote(
                selected,
                correlation_id=operation.correlation_id,
                generar_pdf=False,
            )
            window._procesar_resultado_confirmacion(confirmadas_ids, errores, pendientes_restantes)
            log_event(logger, "confirmar_sin_pdf_finished", {"creadas": len(creadas), "errores": len(errores)}, operation.correlation_id)
            window._show_confirmation_closure(creadas, errores, operation_name="confirmar_sin_pdf", correlation_id=operation.correlation_id)
            window._notify_historico_filter_if_hidden(creadas)
    finally:
        window._set_processing_state(False)


def run_confirmacion_plan(
    window: Any,
    *,
    selected: list[SolicitudDTO],
    selected_ids: list[int | None],
    persona: PersonaDTO | None,
    log_extra: dict[str, Any],
    apply_show_error: Callable[[Any, Any], None],
    apply_prompt_pdf: Callable[[Any, list[SolicitudDTO]], str | None],
    apply_confirm: Callable[[Any, PersonaDTO | None, list[SolicitudDTO], str | None], ResultadoConfirmacionPdf | None],
    apply_finalize: Callable[[Any, PersonaDTO | None, ResultadoConfirmacionPdf | None], None],
) -> None:
    preconfirm_ok = window._run_preconfirm_checks()
    state: dict[str, Any] = {
        "selected": selected,
        "selected_ids": tuple(selected_ids),
        "persona": persona,
        "preconfirm_ok": preconfirm_ok,
        "pdf_prompted": False,
        "pdf_path": None,
        "execute_attempted": False,
        "execute_succeeded": None,
        "outcome": None,
    }

    def return_early(reason: str) -> None:
        logger.warning("UI_CONFIRMAR_PDF_RETURN_EARLY", extra={**log_extra, "reason": reason})
        if reason == "pdf_path_cancelado":
            logger.info("UI_CONFIRMAR_PDF_CANCELLED", extra={**log_extra, "reason": reason})

    while True:
        entrada = ConfirmacionEntrada(
            ui_ready=window._ui_ready,
            selected_ids=state["selected_ids"],
            preconfirm_checks_ok=bool(state["preconfirm_ok"]),
            persona_selected=state["persona"] is not None,
            has_pending_conflicts=bool(window._pending_conflict_rows),
            pdf_prompted=bool(state["pdf_prompted"]),
            pdf_path=state["pdf_path"],
            execute_attempted=bool(state["execute_attempted"]),
            execute_succeeded=state["execute_succeeded"],
        )
        actions = plan_confirmacion(entrada)
        if not actions:
            return
        progressed = _ejecutar_acciones_plan(window, actions, state, return_early, apply_show_error, apply_prompt_pdf, apply_confirm, apply_finalize)
        if not progressed:
            return


def _ejecutar_acciones_plan(
    window: Any,
    actions: tuple[Any, ...],
    state: dict[str, Any],
    return_early: Callable[[str], None],
    apply_show_error: Callable[[Any, Any], None],
    apply_prompt_pdf: Callable[[Any, list[SolicitudDTO]], str | None],
    apply_confirm: Callable[[Any, PersonaDTO | None, list[SolicitudDTO], str | None], ResultadoConfirmacionPdf | None],
    apply_finalize: Callable[[Any, PersonaDTO | None, ResultadoConfirmacionPdf | None], None],
) -> bool:
    for action in actions:
        if action.action_type == "SHOW_ERROR":
            apply_show_error(window, action)
            continue
        if action.action_type == "LOG_EARLY_RETURN":
            logger.info("_on_confirmar early_return motivo=%s", action.reason_code)
            return_early(action.reason_code or "unknown")
            return False
        if action.action_type == "PROMPT_PDF":
            state["pdf_prompted"] = True
            state["pdf_path"] = apply_prompt_pdf(window, state["selected"])
            if state["pdf_path"] is not None:
                logger.debug("_on_confirmar paso=pdf_path_seleccionado path=%s", state["pdf_path"])
            return True
        if action.action_type == "PREPARE_PAYLOAD":
            logger.debug("_on_confirmar paso=llamar_execute_confirmar_with_pdf")
            continue
        if action.action_type == "CONFIRM":
            state["execute_attempted"] = True
            state["outcome"] = apply_confirm(window, state["persona"], state["selected"], state["pdf_path"])
            state["execute_succeeded"] = state["outcome"] is not None
            return True
        if action.action_type == "FINALIZE_CONFIRMATION":
            apply_finalize(window, state["persona"], state["outcome"])
    return False
