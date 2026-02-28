from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from app.core.observability import OperationContext, log_event
from app.application.use_cases.solicitudes.validaciones import validar_seleccion_confirmacion
from app.domain.services import BusinessRuleError, ValidacionError
from app.bootstrap.logging import log_operational_error
from app.ui.notification_service import ConfirmationSummaryPayload
from app.ui.toast_helpers import toast_success
from app.ui.vistas.confirmacion_presenter import ConfirmAction, ConfirmacionEntrada, plan_confirmacion
from app.ui.vistas.pendientes_iter_presenter import IterAction, IterPendientesEntrada, PendienteRowSnapshot, plan_iter_pendientes
from app.ui.vistas.ui_helpers import abrir_archivo_local, abrir_carpeta_contenedora

if TYPE_CHECKING:
    from app.application.dto import PersonaDTO, SolicitudDTO


logger = logging.getLogger(__name__)


def prompt_confirm_pdf_path(window: Any, selected: list[SolicitudDTO]) -> str | None:
    try:
        default_name = window._solicitud_use_cases.sugerir_nombre_pdf(selected)
    except (ValidacionError, BusinessRuleError) as exc:
        window.toast.warning(str(exc), title="Validación")
        return None
    except Exception as exc:  # pragma: no cover - fallback
        logger.exception("Error preparando PDF")
        window._show_critical_error(exc)
        return None

    default_path = str(Path.home() / default_name)
    pdf_path, _ = QFileDialog.getSaveFileName(window, "Guardar PDF", default_path, "PDF (*.pdf)")
    return pdf_path or None


def execute_confirmar_with_pdf(
    window: Any,
    persona: PersonaDTO,
    selected: list[SolicitudDTO],
    pdf_path: str,
) -> tuple[str | None, Path | None, list[SolicitudDTO], list[int], list[str], list[SolicitudDTO] | None] | None:
    correlation_id: str | None = None
    try:
        window._set_processing_state(True)
        with OperationContext("confirmar_y_generar_pdf") as operation:
            correlation_id = operation.correlation_id
            logger.debug("_execute_confirmar_with_pdf paso=validar_seleccion count=%s", len(selected))
            logger.debug("_execute_confirmar_with_pdf paso=ids_seleccionadas ids=%s", [sol.id for sol in selected])
            log_event(
                logger,
                "confirmar_y_generar_pdf_started",
                {"count": len(selected), "destino": pdf_path},
                operation.correlation_id,
            )
            confirmadas_ids, errores, generado, creadas, pendientes_restantes = window._solicitudes_controller.confirmar_lote(
                selected,
                correlation_id=operation.correlation_id,
                generar_pdf=True,
                pdf_path=pdf_path,
                filtro_delegada=None if window._pending_view_all else (persona.id or None),
            )
            logger.debug("_execute_confirmar_with_pdf paso=llamada_servicio_confirmar ok=True")
            logger.debug("_execute_confirmar_with_pdf paso=llamada_generador_pdf ruta=%s", str(generado) if generado else "")
            log_event(
                logger,
                "confirmar_y_generar_pdf_finished",
                {"creadas": len(creadas), "errores": len(errores), "pdf_generado": bool(generado)},
                operation.correlation_id,
            )
            return correlation_id, generado, creadas, confirmadas_ids, errores, pendientes_restantes
    except Exception as exc:  # pragma: no cover - fallback
        if isinstance(exc, OSError):
            log_operational_error(
                logger,
                "File export failed during confirm+PDF",
                exc=exc,
                extra={
                    "operation": "confirmar_y_generar_pdf",
                    "persona_id": persona.id or 0,
                    "correlation_id": correlation_id,
                },
            )
        else:
            logger.exception("Error confirmando solicitudes")
        window._show_critical_error(exc)
        return None
    finally:
        window._set_processing_state(False)


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
    if generado and window.abrir_pdf_check.isChecked():
        logger.debug("_finalize_confirmar_with_pdf paso=intento_abrir_pdf enabled=True")
        abrir_archivo_local(generado)
    if generado and creadas:
        pdf_hash = creadas[0].pdf_hash
        fechas = [solicitud.fecha_pedida for solicitud in creadas]
        window._sync_service.register_pdf_log(persona.id or 0, fechas, pdf_hash)
        if correlation_id:
            log_event(
                logger,
                "register_pdf_log",
                {"persona_id": persona.id or 0, "fechas": len(fechas)},
                correlation_id,
            )
        window._ask_push_after_pdf()
        window._toast_success("PDF generado correctamente", title="Confirmación")
        if generado.exists():
            window._show_pdf_actions_dialog(generado)
    window._procesar_resultado_confirmacion(confirmadas_ids, errores, pendientes_restantes)
    window._show_confirmation_closure(
        creadas,
        errores,
        operation_name="confirmar_y_generar_pdf",
        correlation_id=correlation_id,
    )
    window._notify_historico_filter_if_hidden(creadas)


def show_pdf_actions_dialog(window: Any, generated_path: Path) -> None:
    if not generated_path.exists():
        return
    dialog = QMessageBox(window)
    dialog.setWindowTitle("PDF generado")
    dialog.setText("PDF generado correctamente")
    open_pdf_button = dialog.addButton("Abrir PDF", QMessageBox.ButtonRole.ActionRole)
    open_folder_button = dialog.addButton("Abrir carpeta", QMessageBox.ButtonRole.ActionRole)
    close_button = dialog.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
    dialog.exec()
    clicked = dialog.clickedButton()
    if clicked is open_pdf_button:
        abrir_archivo_local(generated_path)
    elif clicked is open_folder_button:
        abrir_carpeta_contenedora(generated_path)
    elif clicked is close_button:
        return


def sum_solicitudes_minutes(solicitudes: list[SolicitudDTO]) -> int:
    return sum(int(round(solicitud.horas * 60)) for solicitud in solicitudes)


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
        {
            "operation": operation_name,
            "result_id": payload.result_id,
            "status": payload.status,
            "count": payload.count,
            "delegadas": payload.delegadas,
            "total_minutes": payload.total_minutes,
            "saldo_disponible": payload.saldo_disponible,
            "errores": payload.errores,
            "timestamp": payload.timestamp,
        },
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
    delegadas = sorted({persona_nombres.get(s.persona_id, f"ID {s.persona_id}") for s in creadas})
    if not creadas:
        status = "error"
    elif errores:
        status = "partial"
    else:
        status = "success"
    undo_ids = [solicitud.id for solicitud in creadas if solicitud.id is not None]
    return ConfirmationSummaryPayload(
        count=len(creadas),
        total_minutes=sum_solicitudes_minutes(creadas),
        delegadas=delegadas,
        saldo_disponible=window.saldos_card.saldo_periodo_restante_text(),
        errores=errores,
        status=status,
        timestamp=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        result_id=f"CFM-{datetime.now().strftime('%y%m%d%H%M%S')}",
        correlation_id=correlation_id,
        on_view_history=window._focus_historico_search,
        on_sync_now=window._on_push_now,
        on_return_to_operativa=lambda: window.main_tabs.setCurrentIndex(0),
        undo_seconds=12 if undo_ids else None,
        on_undo=(lambda: window._undo_confirmation(undo_ids)) if undo_ids else None,
    )


def undo_confirmation(window: Any, solicitud_ids: list[int]) -> None:
    if window._sync_in_progress:
        window.toast.warning("La sincronización está en curso. Ahora no se puede deshacer.", title="Deshacer no disponible")
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
        toast_success(window.toast, f"Se deshicieron {removed} confirmaciones.")


def ask_push_after_pdf(window: Any) -> None:
    dialog = QMessageBox(window)
    dialog.setWindowTitle("PDF generado")
    dialog.setText("PDF generado. ¿Quieres sincronizar ahora con Google Sheets?")
    subir_button = dialog.addButton("Subir ahora", QMessageBox.AcceptRole)
    dialog.addButton("Más tarde", QMessageBox.RejectRole)
    dialog.exec()
    if dialog.clickedButton() != subir_button:
        return
    window._on_push_now()


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
        window.toast.warning(warning_message, title="Selección requerida")
        logger.info("_on_insertar_sin_pdf early_return motivo=sin_seleccion")
        return
    if window._pending_conflict_rows:
        logger.info("_on_insertar_sin_pdf early_return motivo=conflictos_pendientes")
        window.toast.warning(
            "Hay peticiones con horarios solapados. Elimina/modifica el conflicto para confirmar.",
            title="Conflictos detectados",
        )
        return

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
            log_event(
                logger,
                "confirmar_sin_pdf_finished",
                {"creadas": len(creadas), "errores": len(errores)},
                operation.correlation_id,
            )
            window._show_confirmation_closure(
                creadas,
                errores,
                operation_name="confirmar_sin_pdf",
                correlation_id=operation.correlation_id,
            )
            window._notify_historico_filter_if_hidden(creadas)
    finally:
        window._set_processing_state(False)


def on_confirmar(window: Any) -> None:
    try:
        logger.info("CLICK confirmar_pdf handler=_on_confirmar")
        window._dump_estado_pendientes("click_confirmar_pdf")
        pendientes_en_tabla = iterar_pendientes_en_tabla(window)
        logger.debug("DEBUG_PENDIENTES_COUNT %s", len(pendientes_en_tabla))
        for pendiente in pendientes_en_tabla:
            logger.debug("DEBUG_PENDIENTE %s", pendiente)

        selected = [
            window.pendientes_model.solicitud_at(item["row"])
            for item in pendientes_en_tabla
            if window.pendientes_model is not None
        ]
        selected = [sol for sol in selected if sol is not None]
        selected_ids = [sol.id for sol in selected]
        editing = window._selected_pending_for_editing()
        persona = window._current_persona()
        log_extra = {
            "selected_count": len(selected),
            "selected_ids": selected_ids,
            "editing_id": editing.id if editing is not None else None,
            "persona_id": persona.id if persona is not None else None,
            "fecha": window.fecha_input.date().toString("yyyy-MM-dd"),
            "desde": window.desde_input.time().toString("HH:mm"),
            "hasta": window.hasta_input.time().toString("HH:mm"),
        }
        logger.info("UI_CLICK_CONFIRMAR_PDF", extra=log_extra)
        logger.debug("_on_confirmar paso=seleccion_pendientes rows=%s ids=%s", window._selected_pending_row_indexes(), selected_ids)
        _run_confirmacion_plan(window, selected, selected_ids, persona, log_extra)
    except Exception:
        logger.exception("UI_CONFIRMAR_PDF_EXCEPTION")
        raise


def _run_confirmacion_plan(
    window: Any,
    selected: list[SolicitudDTO],
    selected_ids: list[int | None],
    persona: PersonaDTO | None,
    log_extra: dict[str, Any],
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

    def _return_early(reason: str) -> None:
        logger.warning("UI_CONFIRMAR_PDF_RETURN_EARLY", extra={**log_extra, "reason": reason})

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

        progressed = False
        for action in actions:
            if action.action_type == "SHOW_ERROR":
                _apply_show_error(window, action)
                continue
            if action.action_type == "LOG_EARLY_RETURN":
                logger.info("_on_confirmar early_return motivo=%s", action.reason_code)
                _return_early(action.reason_code or "unknown")
                return
            if action.action_type == "PROMPT_PDF":
                pdf_path = _apply_prompt_pdf(window, state["selected"])
                state["pdf_prompted"] = True
                state["pdf_path"] = pdf_path
                if pdf_path is not None:
                    logger.debug("_on_confirmar paso=pdf_path_seleccionado path=%s", pdf_path)
                progressed = True
                break
            if action.action_type == "PREPARE_PAYLOAD":
                logger.debug("_on_confirmar paso=llamar_execute_confirmar_with_pdf")
                continue
            if action.action_type == "CONFIRM":
                state["execute_attempted"] = True
                outcome = _apply_confirm(window, state["persona"], state["selected"], state["pdf_path"])
                state["outcome"] = outcome
                state["execute_succeeded"] = outcome is not None
                progressed = True
                break
            if action.action_type == "FINALIZE_CONFIRMATION":
                _apply_finalize(window, state["persona"], state["outcome"])
                continue
            if action.action_type in {"RESET_FORM", "REFRESH_TABLE", "SHOW_TOAST"}:
                continue

        if not progressed:
            return


def _apply_show_error(window: Any, action: ConfirmAction) -> None:
    if action.message:
        window.toast.warning(action.message, title=action.title or "Validación")


def _apply_prompt_pdf(window: Any, selected: list[SolicitudDTO]) -> str | None:
    return window._prompt_confirm_pdf_path(selected)


def _apply_confirm(window: Any, persona: PersonaDTO | None, selected: list[SolicitudDTO], pdf_path: str | None) -> tuple[str | None, Path | None, list[SolicitudDTO], list[int], list[str], list[SolicitudDTO] | None] | None:
    if persona is None or pdf_path is None:
        return None
    return window._execute_confirmar_with_pdf(persona, selected, pdf_path)


def _apply_finalize(
    window: Any,
    persona: PersonaDTO | None,
    outcome: tuple[str | None, Path | None, list[SolicitudDTO], list[int], list[str], list[SolicitudDTO] | None] | None,
) -> None:
    if persona is None or outcome is None:
        return
    correlation_id, generado, creadas, confirmadas_ids, errores, pendientes_restantes = outcome
    logger.debug("_on_confirmar paso=resultado_execute pdf_generado=%s", str(generado) if generado else None)
    window._finalize_confirmar_with_pdf(persona, correlation_id, generado, creadas, confirmadas_ids, errores, pendientes_restantes)


def iterar_pendientes_en_tabla(window: Any) -> list[dict[str, object]]:
    model = window.pendientes_table.model() if window.pendientes_table is not None else None
    if model is None:
        return []

    snapshots = _build_pendientes_snapshots(window, model)
    plan = plan_iter_pendientes(IterPendientesEntrada(ui_ready=True, rows=tuple(snapshots)))
    return _apply_iter_pendientes_actions(plan.actions)


def _build_pendientes_snapshots(window: Any, model: Any) -> list[PendienteRowSnapshot]:
    total_rows = model.rowCount()
    total_cols = model.columnCount()
    delegada_col = _find_delegada_col(model, total_cols)
    snapshots: list[PendienteRowSnapshot] = []
    for row in range(total_rows):
        solicitud = window.pendientes_model.solicitud_at(row) if window.pendientes_model is not None else None
        snapshots.append(
            PendienteRowSnapshot(
                row=row,
                solicitud_id=solicitud.id if solicitud is not None else None,
                persona_id=solicitud.persona_id if solicitud is not None else None,
                fecha_raw=model.index(row, 0).data() if total_cols > 0 else "",
                desde_raw=model.index(row, 1).data() if total_cols > 1 else "",
                hasta_raw=model.index(row, 2).data() if total_cols > 2 else "",
                delegada_raw=model.index(row, delegada_col).data() if delegada_col is not None else None,
            )
        )
    return snapshots


def _find_delegada_col(model: Any, total_cols: int) -> int | None:
    for col in range(total_cols):
        header = model.headerData(col, Qt.Horizontal, Qt.DisplayRole)
        if str(header).strip().lower() == "delegada":
            return col
    return None


def _apply_iter_pendientes_actions(actions: tuple[IterAction, ...]) -> list[dict[str, object]]:
    pendientes: list[dict[str, object]] = []
    for action in actions:
        if action.action_type != "APPEND_PENDING":
            continue
        pendientes.append(_apply_append_pending(action))
    return pendientes


def _apply_append_pending(action: IterAction) -> dict[str, object]:
    return dict(action.payload)
