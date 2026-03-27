from __future__ import annotations

from datetime import datetime
import logging

try:
    from PySide6.QtCore import QThread
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover
    QThread = object
    QApplication = None

from app.domain.sheets_errors import SheetsPermissionError
from app.domain.sync_models import SyncAttemptReport, SyncExecutionPlan, SyncSummary
from app.ui import dialogos_comunes
from app.ui.conflicts_dialog import ConflictsDialog
from app.ui.error_mapping import map_error_to_ui_message
from app.ui.notification_service import OperationFeedback
from app.ui.sync_reporting import build_config_incomplete_report, build_failed_report, build_simulation_report, build_sync_report
import app.ui.vistas.main_window.dialogos_sincronizacion as dialogos_sincronizacion
from app.ui.vistas.main_window_helpers import show_sync_error_dialog_from_exception
from app.ui.workers.sincronizacion_workers import PushWorker
from app.bootstrap.logging import log_operational_error
from app.ui.i18n_interfaz import texto_interfaz

logger = logging.getLogger(__name__)


def on_sync_finished(ventana, summary: SyncSummary) -> None:
    ventana._pending_sync_plan = None
    ventana._solicitudes_runtime_error = False
    ventana.confirm_sync_button.setEnabled(False)
    set_sync_in_progress(ventana, False)
    ventana._solicitudes_runtime_error = True
    update_sync_button_state(ventana)
    ventana._update_solicitudes_status_panel()
    ventana._refresh_last_sync_label()
    status = dialogos_sincronizacion.status_from_summary(summary)
    next_attempt_history = tuple([*ventana._attempt_history, SyncAttemptReport(
        attempt_number=len(ventana._attempt_history) + 1,
        status=status,
        created=summary.inserted_local + summary.inserted_remote,
        updated=summary.updated_local + summary.updated_remote,
        conflicts=summary.conflicts_detected,
        errors=summary.errors,
    )])
    report = build_sync_report(
        summary,
        status=status,
        source=dialogos_sincronizacion.sync_source_text(ventana),
        scope=dialogos_sincronizacion.sync_scope_text(),
        actor=dialogos_sincronizacion.sync_actor_text(ventana),
        started_at=ventana._sync_started_at,
        sync_id=ventana._active_sync_id,
        attempt_history=next_attempt_history,
    )
    ventana._active_sync_id = report.sync_id
    ventana._attempt_history = next_attempt_history
    apply_sync_report(ventana, report)
    refresh_after_sync(ventana, summary)
    feedback_status = "success"
    incidents = "Sin incidencias."
    if status == "OK_WARN":
        feedback_status = "partial"
        incidents = f"{summary.conflicts_detected} conflictos y {summary.errors} errores."
    elif status == "ERROR":
        feedback_status = "error"
        incidents = "La sincronización no se pudo completar."
    ventana.notifications.notify_operation(OperationFeedback(
        title=f"Resultado de sincronización: {ventana._status_to_label(status)}",
        happened="Se actualizó el estado del panel con el resumen persistente.",
        affected_count=summary.inserted_local + summary.inserted_remote + summary.updated_local + summary.updated_remote,
        incidents=incidents,
        next_step="Revisa conflictos o continúa operando según el estado mostrado.",
        status=feedback_status,
    ))
    dialogos_sincronizacion.show_sync_summary_dialog(ventana, f"Resultado: {ventana._status_to_label(status)}", summary)


def on_sync_simulation_finished(ventana, plan: SyncExecutionPlan) -> None:
    set_sync_in_progress(ventana, False)
    ventana._pending_sync_plan = plan
    update_sync_button_state(ventana)
    report = build_simulation_report(
        plan,
        source=dialogos_sincronizacion.sync_source_text(ventana),
        scope=dialogos_sincronizacion.sync_scope_text(),
        actor=dialogos_sincronizacion.sync_actor_text(ventana),
        sync_id=ventana._active_sync_id,
        attempt_history=ventana._attempt_history,
    )
    apply_sync_report(ventana, report)
    has_changes = plan.has_changes
    ventana.confirm_sync_button.setEnabled(has_changes and not bool(plan.conflicts))
    ventana.retry_failed_button.setEnabled(bool(plan.conflicts or plan.potential_errors))
    if has_changes:
        ventana.toast.info(f"Se crearán: {len(plan.to_create)} · Se actualizarán: {len(plan.to_update)} · Sin cambios: {len(plan.unchanged)} · Conflictos detectados: {len(plan.conflicts)}", title="Simulación completada", duration_ms=7000)
    else:
        ventana.toast.info("No hay cambios que aplicar", title="Simulación completada")


def refresh_after_sync(ventana, summary: SyncSummary) -> None:
    ventana._refresh_historico()
    ventana._refresh_saldos()
    ventana._refresh_pending_ui_state()
    if summary.inserted_local <= 0:
        return
    persona = ventana._current_persona()
    if persona is None or ventana.historico_proxy_model.rowCount() > 0 or persona.id is None:
        return
    if any(True for _ in ventana._solicitud_use_cases.listar_solicitudes_por_persona(persona.id)):
        ventana.toast.info("Datos importados, pero no visibles por los filtros actuales de histórico.", title="Sincronización")


def on_sync_failed(ventana, payload: object) -> None:
    set_sync_in_progress(ventana, False)
    ventana._solicitudes_runtime_error = True
    update_sync_button_state(ventana)
    ventana._update_solicitudes_status_panel()
    error, details = normalize_sync_error(payload)
    if details:
        log_operational_error(logger, "Sync failed", exc=error, extra={"operation": "sync_ui", "correlation_id": getattr(ventana._sync_operation_context, "correlation_id", None), "sync_id": ventana._active_sync_id})
    if isinstance(error, SheetsPermissionError):
        _log_sync_permission_error(ventana, error)
        report = build_config_incomplete_report(
            source=dialogos_sincronizacion.sync_source_text(ventana),
            scope=dialogos_sincronizacion.sync_scope_text(),
            actor=dialogos_sincronizacion.sync_actor_text(ventana),
        )
    else:
        report = build_failed_report(
            map_error_to_ui_message(error).as_text(),
            source=dialogos_sincronizacion.sync_source_text(ventana),
            scope=dialogos_sincronizacion.sync_scope_text(),
            actor=dialogos_sincronizacion.sync_actor_text(ventana),
            details=details,
            started_at=ventana._sync_started_at,
            sync_id=ventana._active_sync_id,
            attempt_history=ventana._attempt_history,
        )
    apply_sync_report(ventana, report)
    ventana.notifications.notify_operation(OperationFeedback(title="Sincronización con fallo", happened="No se pudo completar la sincronización.", affected_count=0, incidents="Se detectó un error durante el proceso.", next_step="Revisa el detalle y vuelve a intentar.", status="error"))
    show_sync_error_dialog(ventana, error, details)


def _log_sync_permission_error(ventana, error: SheetsPermissionError) -> None:
    log_operational_error(
        logger,
        "Sincronización bloqueada por permisos en Google Sheets",
        exc=error,
        extra={
            "operation": "sheets_permission_check",
            "spreadsheet_id": error.spreadsheet_id,
            "worksheet": error.worksheet,
            "service_email": error.service_account_email or dialogos_sincronizacion.service_account_email(ventana),
            "correlation_id": getattr(getattr(ventana, "_sync_operation_context", None), "correlation_id", None),
        },
    )


def on_push_now(ventana) -> None:
    if not ventana._sync_service.is_configured():
        ventana.toast.warning(texto_interfaz("ui.sync.panel.no_hay_configuracion"), title=texto_interfaz("ui.sync.panel.sin_configuracion"))
        return
    set_sync_in_progress(ventana, True)
    ventana._sync_thread = QThread()
    ventana._sync_worker = PushWorker(ventana._sync_service)
    ventana._sync_worker.moveToThread(ventana._sync_thread)
    ventana._sync_thread.started.connect(ventana._sync_worker.run)
    ventana._sync_worker.finished.connect(ventana._on_push_finished)
    ventana._sync_worker.failed.connect(ventana._on_push_failed)
    ventana._sync_worker.finished.connect(ventana._sync_thread.quit)
    ventana._sync_worker.finished.connect(ventana._sync_worker.deleteLater)
    ventana._sync_thread.finished.connect(ventana._sync_thread.deleteLater)
    ventana._sync_thread.start()


def on_push_finished(ventana, summary: SyncSummary) -> None:
    set_sync_in_progress(ventana, False)
    ventana._solicitudes_runtime_error = True
    update_sync_button_state(ventana)
    ventana._update_solicitudes_status_panel()
    if summary.conflicts_detected > 0:
        ConflictsDialog(ventana._conflicts_service, ventana).exec()
    ventana._refresh_last_sync_label()
    dialogos_sincronizacion.show_sync_summary_dialog(ventana, texto_interfaz("ui.sync.panel.sincronizacion_completada"), summary)


def on_push_failed(ventana, payload: object) -> None:
    set_sync_in_progress(ventana, False)
    ventana._solicitudes_runtime_error = True
    update_sync_button_state(ventana)
    ventana._update_solicitudes_status_panel()
    error, details = normalize_sync_error(payload)
    show_sync_error_dialog(ventana, error, details)


def update_sync_button_state(ventana) -> None:
    ventana._sync_controller.update_sync_button_state()


def update_conflicts_reminder(ventana) -> None:
    reminder_label = getattr(ventana, "conflicts_reminder_label", None)
    if reminder_label is None:
        return

    try:
        total = _safe_conflicts_count(ventana)
        reminder_label.setVisible(total > 0)
        if total <= 0:
            return
        reminder_label.setText(texto_interfaz("ui.sync.panel.conflictos_pendientes", cantidad=total))
    except Exception:
        logger.exception("UI_UPDATE_CONFLICTS_REMINDER_FAILED")


def _safe_conflicts_count(ventana) -> int:
    service = getattr(ventana, "_conflicts_service", None)
    if service is None or not hasattr(service, "count_conflicts"):
        return 0
    raw_total = service.count_conflicts()
    if isinstance(raw_total, bool) or not isinstance(raw_total, (int, float)):
        return 0
    return max(int(raw_total), 0)


def show_sync_error_dialog(ventana, error: Exception, details: str | None) -> None:
    show_sync_error_dialog_from_exception(
        error=error,
        details=details,
        service_account_email=dialogos_sincronizacion.service_account_email(ventana),
        show_message_with_details=lambda title, message, detail, icon, action_buttons=(): dialogos_comunes.show_message_with_details(
            ventana, title, message, detail, icon, action_buttons
        ),
        open_options_callback=ventana._on_open_opciones,
        retry_callback=ventana._sync_controller.on_sync,
        open_google_sheets_config_callback=ventana._open_google_sheets_config,
        toast_warning=lambda message, title, duration_ms: ventana.toast.warning(message, title=title, duration_ms=duration_ms),
        clipboard_setter=_set_clipboard_text,
    )


def _set_clipboard_text(value: str) -> None:
    if QApplication is None:
        raise RuntimeError("Clipboard no disponible: Qt no está inicializado")
    clipboard = QApplication.clipboard()
    if clipboard is None:
        raise RuntimeError("Clipboard no disponible")
    clipboard.setText(value)



def normalize_sync_error(payload: object) -> tuple[Exception, str | None]:
    if isinstance(payload, dict):
        error = payload.get("error")
        details = payload.get("details")
        if isinstance(error, Exception):
            return error, details
        return Exception(str(error)), details
    if isinstance(payload, Exception):
        return payload, None
    return Exception(str(payload)), None


def set_sync_in_progress(ventana, in_progress: bool) -> None:
    ventana._sync_in_progress = in_progress
    ventana.sync_status_label.setVisible(in_progress)
    ventana.sync_progress.setVisible(in_progress)
    if ventana.status_sync_label is not None:
        ventana.status_sync_label.setVisible(in_progress)
    if ventana.status_sync_progress is not None:
        ventana.status_sync_progress.setVisible(in_progress)
    if in_progress:
        ventana._sync_started_at = datetime.now().isoformat()
        ventana.statusBar().showMessage(texto_interfaz("ui.sync.panel.sincronizando_sheets"))
        ventana.sync_button.setEnabled(False)
        ventana.simulate_sync_button.setEnabled(False)
        ventana.confirm_sync_button.setEnabled(False)
        ventana.sync_details_button.setEnabled(False)
        ventana.copy_sync_report_button.setEnabled(False)
        ventana.review_conflicts_button.setEnabled(False)
        dialogos_sincronizacion.set_sync_status_badge(ventana, "RUNNING")
        ventana.sync_panel_status.setText(texto_interfaz("ui.sync.panel.estado_pendiente_sincronizando"))
    else:
        ventana.statusBar().clearMessage()


def apply_sync_report(ventana, report) -> None:
    dialogos_sincronizacion.apply_sync_report(ventana, report)


def set_config_incomplete_state(ventana) -> None:
    report = build_config_incomplete_report(
        source=dialogos_sincronizacion.sync_source_text(ventana),
        scope=dialogos_sincronizacion.sync_scope_text(),
        actor=dialogos_sincronizacion.sync_actor_text(ventana),
    )
    apply_sync_report(ventana, report)
    ventana.go_to_sync_config_button.setVisible(True)
