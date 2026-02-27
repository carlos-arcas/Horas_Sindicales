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

        def _return_early(reason: str) -> None:
            logger.warning("UI_CONFIRMAR_PDF_RETURN_EARLY", extra={**log_extra, "reason": reason})

        if not window._ui_ready:
            logger.info("_on_confirmar early_return motivo=ui_not_ready")
            _return_early("ui_not_ready")
            return
        logger.debug("_on_confirmar paso=validar_preconfirm_checks")
        if not selected:
            window.toast.warning("No hay pendientes", title="Sin pendientes")
            logger.info("_on_confirmar early_return motivo=no_pending_rows")
            _return_early("no_pending_rows")
            return
        if not window._run_preconfirm_checks():
            logger.info("_on_confirmar early_return motivo=preconfirm_checks")
            _return_early("preconfirm_checks")
            return
        logger.debug("_on_confirmar paso=seleccion_pendientes rows=%s ids=%s", window._selected_pending_row_indexes(), selected_ids)
        if persona is None:
            logger.info("_on_confirmar early_return motivo=no_persona")
            _return_early("no_persona")
            return
        if window._pending_conflict_rows:
            logger.info("_on_confirmar early_return motivo=conflictos_pendientes")
            window.toast.warning(
                "Hay peticiones con horarios solapados. Elimina/modifica el conflicto para confirmar.",
                title="Conflictos detectados",
            )
            _return_early("conflictos_pendientes")
            return

        pdf_path = window._prompt_confirm_pdf_path(selected)
        if pdf_path is None:
            logger.info("_on_confirmar early_return motivo=pdf_path_cancelado")
            _return_early("pdf_path_cancelado")
            return
        logger.debug("_on_confirmar paso=pdf_path_seleccionado path=%s", pdf_path)

        logger.debug("_on_confirmar paso=llamar_execute_confirmar_with_pdf")
        outcome = window._execute_confirmar_with_pdf(persona, selected, pdf_path)
        if outcome is None:
            logger.info("_on_confirmar early_return motivo=execute_confirmar_none")
            _return_early("execute_confirmar_none")
            return
        correlation_id, generado, creadas, confirmadas_ids, errores, pendientes_restantes = outcome
        logger.debug("_on_confirmar paso=resultado_execute pdf_generado=%s", str(generado) if generado else None)

        window._finalize_confirmar_with_pdf(persona, correlation_id, generado, creadas, confirmadas_ids, errores, pendientes_restantes)
    except Exception:
        logger.exception("UI_CONFIRMAR_PDF_EXCEPTION")
        raise


def iterar_pendientes_en_tabla(window: Any) -> list[dict[str, object]]:
    if window.pendientes_table is None:
        return []
    model = window.pendientes_table.model()
    if model is None:
        return []

    total_rows = model.rowCount()
    total_cols = model.columnCount()
    delegada_col: int | None = None
    for col in range(total_cols):
        header = model.headerData(col, Qt.Horizontal, Qt.DisplayRole)
        if str(header).strip().lower() == "delegada":
            delegada_col = col
            break

    pendientes: list[dict[str, object]] = []
    for row in range(total_rows):
        solicitud = window.pendientes_model.solicitud_at(row) if window.pendientes_model is not None else None
        fecha = model.index(row, 0).data() if total_cols > 0 else ""
        desde = model.index(row, 1).data() if total_cols > 1 else ""
        hasta = model.index(row, 2).data() if total_cols > 2 else ""
        delegada = model.index(row, delegada_col).data() if delegada_col is not None else None
        pendientes.append(
            {
                "row": row,
                "id": solicitud.id if solicitud is not None else None,
                "fecha": fecha if fecha not in (None, "-") else "",
                "desde": desde if desde not in (None, "-") else "",
                "hasta": hasta if hasta not in (None, "-") else "",
                "persona_id": solicitud.persona_id if solicitud is not None else None,
                "delegada": delegada if delegada not in (None, "-") else None,
            }
        )
    return pendientes
