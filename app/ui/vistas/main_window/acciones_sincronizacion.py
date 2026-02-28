from __future__ import annotations

import logging
try:
    from PySide6.QtWidgets import QApplication, QMessageBox
except Exception:  # pragma: no cover
    QApplication = QMessageBox = object

from app.domain.sync_models import SyncExecutionPlan, SyncSummary
from app.ui.conflicts_dialog import ConflictsDialog
from app.ui.notification_service import OperationFeedback
from app.ui.sync_reporting import to_markdown
from app.ui.vistas.main_window import acciones_sincronizacion_resultados as resultados
from app.ui.vistas.main_window import dialogos_sincronizacion
from app.ui.vistas.ui_helpers import abrir_archivo_local
from app.bootstrap.logging import log_operational_error

logger = logging.getLogger(__name__)


def on_sync(ventana) -> None:
    if not ventana._ui_ready:
        return
    if hasattr(ventana._sync_service, "is_configured") and not ventana._sync_service.is_configured():
        ventana.toast.warning("Falta configurar Google Sheets o compartir la hoja con la cuenta de servicio.", title="Sync no disponible")
        return
    ventana._pending_sync_plan = None
    ventana._active_sync_id = None
    ventana._attempt_history = ()
    ventana._sync_attempts = []
    ventana.confirm_sync_button.setEnabled(False)
    ventana._sync_controller.on_sync()


def on_simulate_sync(ventana) -> None:
    ventana._sync_controller.on_simulate_sync()


def on_confirm_sync(ventana) -> None:
    if ventana._pending_sync_plan is not None and ventana._pending_sync_plan.conflicts:
        ventana.toast.warning("Conflictos pendientes de decisión", title="Sincronización bloqueada")
        return
    ventana._sync_controller.on_confirm_sync()


def on_retry_failed(ventana) -> None:
    if ventana._pending_sync_plan is None or ventana._last_sync_report is None:
        ventana.notifications.notify_operation(OperationFeedback(
            title="Reintento no disponible",
            happened="No hay un plan fallido que se pueda reintentar.",
            affected_count=0,
            incidents="No hay incidencias nuevas.",
            next_step="Ejecuta una sincronización y revisa conflictos si aparecen.",
            status="error",
        ))
        return
    item_status = {
        item.uuid: ("CONFLICT" if item in ventana._pending_sync_plan.conflicts else "ERROR")
        for item in [*ventana._pending_sync_plan.to_create, *ventana._pending_sync_plan.to_update, *ventana._pending_sync_plan.conflicts]
    }
    retry_result = ventana._retry_sync_use_case.build_retry_plan(ventana._pending_sync_plan, item_status=item_status)
    ventana._pending_sync_plan = retry_result.plan
    ventana.notifications.notify_operation(OperationFeedback(
        title="Reintento preparado",
        happened="Se reconstruyó el plan con los elementos en conflicto o error.",
        affected_count=len(item_status),
        incidents="Pendiente de ejecución.",
        next_step="Pulsa sincronizar para completar el reintento.",
    ))
    ventana._sync_controller.on_confirm_sync()


def on_show_sync_details(ventana) -> None:
    if ventana._last_sync_report is None:
        ventana.toast.info("Todavía no hay informes de sincronización.", title="Sincronización")
        return
    dialogos_sincronizacion.show_sync_details_dialog(ventana)


def on_copy_sync_report(ventana) -> None:
    if ventana._last_sync_report is None:
        return
    QApplication.clipboard().setText(to_markdown(ventana._last_sync_report))
    ventana._toast_success("Informe copiado al portapapeles.", title="Sincronización")


def on_open_sync_logs(ventana) -> None:
    ventana._logs_dir.mkdir(parents=True, exist_ok=True)
    abrir_archivo_local(ventana._logs_dir)


def on_review_conflicts(ventana) -> None:
    ConflictsDialog(ventana._conflicts_service, ventana).exec()
    resultados.update_sync_button_state(ventana)
    resultados.update_conflicts_reminder(ventana)


def on_open_opciones(ventana) -> None:
    ventana._sync_controller.on_open_opciones()


def open_google_sheets_config(ventana) -> None:
    on_open_opciones(ventana)


def on_sync_finished(ventana, summary: SyncSummary) -> None:
    resultados.on_sync_finished(ventana, summary)


def on_sync_simulation_finished(ventana, plan: SyncExecutionPlan) -> None:
    resultados.on_sync_simulation_finished(ventana, plan)


def refresh_after_sync(ventana, summary: SyncSummary) -> None:
    resultados.refresh_after_sync(ventana, summary)


def on_sync_failed(ventana, payload: object) -> None:
    resultados.on_sync_failed(ventana, payload)


def on_push_now(ventana) -> None:
    resultados.on_push_now(ventana)


def on_push_finished(ventana, summary: SyncSummary) -> None:
    resultados.on_push_finished(ventana, summary)


def on_push_failed(ventana, payload: object) -> None:
    resultados.on_push_failed(ventana, payload)


def update_sync_button_state(ventana) -> None:
    resultados.update_sync_button_state(ventana)


def update_conflicts_reminder(ventana) -> None:
    resultados.update_conflicts_reminder(ventana)


def show_sync_error_dialog(ventana, error: Exception, details: str | None) -> None:
    resultados.show_sync_error_dialog(ventana, error, details)


def apply_sync_report(ventana, report) -> None:
    resultados.apply_sync_report(ventana, report)


def on_show_sync_history(ventana) -> None:
    dialogos_sincronizacion.on_show_sync_history(ventana)


def show_sync_details_dialog(ventana) -> None:
    dialogos_sincronizacion.show_sync_details_dialog(ventana)


def set_sync_status_badge(ventana, status: str) -> None:
    dialogos_sincronizacion.set_sync_status_badge(ventana, status)


def status_from_summary(summary: SyncSummary) -> str:
    return dialogos_sincronizacion.status_from_summary(summary)


def status_to_label(status: str) -> str:
    return dialogos_sincronizacion.status_to_label(status)


def sync_source_text(ventana) -> str:
    return dialogos_sincronizacion.sync_source_text(ventana)


def sync_scope_text() -> str:
    return dialogos_sincronizacion.sync_scope_text()


def sync_actor_text(ventana) -> str:
    return dialogos_sincronizacion.sync_actor_text(ventana)


def show_sync_summary_dialog(ventana, title: str, summary: SyncSummary) -> None:
    dialogos_sincronizacion.show_sync_summary_dialog(ventana, title, summary)


def normalize_sync_error(payload: object) -> tuple[Exception, str | None]:
    return resultados.normalize_sync_error(payload)


def set_sync_in_progress(ventana, in_progress: bool) -> None:
    resultados.set_sync_in_progress(ventana, in_progress)


def service_account_email(ventana) -> str | None:
    return dialogos_sincronizacion.service_account_email(ventana)


def set_config_incomplete_state(ventana) -> None:
    resultados.set_config_incomplete_state(ventana)


def sincronizar_con_confirmacion(ventana) -> None:
    result = QMessageBox.question(
        ventana,
        "Confirmar sincronización",
        "¿Deseas iniciar la sincronización con Google Sheets ahora?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if result != QMessageBox.StandardButton.Yes:
        return
    sync_handler = getattr(ventana, "_on_sync", None)
    if callable(sync_handler):
        sync_handler()
        return
    logger.error("sync_handler_missing", extra={"handler": "_on_sync"})
    QMessageBox.information(ventana, "Sincronización", "La sincronización aún no está disponible en esta pantalla.")


def on_sync_with_confirmation(ventana) -> None:
    result = QMessageBox.question(
        ventana,
        "Confirmar sincronización",
        "¿Deseas iniciar la sincronización con Google Sheets ahora?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if result != QMessageBox.StandardButton.Yes:
        return
    try:
        if hasattr(ventana, "_sync_controller") and callable(getattr(ventana._sync_controller, "on_sync", None)):
            ventana._sync_controller.on_sync()
            return
        if callable(getattr(ventana, "_on_sync", None)):
            ventana._on_sync()
            return
        logger.warning("sync_workflow_not_available")
        QMessageBox.information(ventana, "Sincronización", "Función no disponible")
    except Exception as exc:  # pragma: no cover
        log_operational_error(
            logger,
            "Sync failed: no se pudo iniciar desde UI",
            exc=exc,
            extra={"operation": "sync_workflow_start"},
        )
        QMessageBox.critical(ventana, "Sincronización", f"No se pudo iniciar la sincronización.\n\n{exc}")


def show_message_with_details(ventana, title: str, message: str, details: str | None, icon, action_buttons: tuple[tuple[str, object], ...] = ()) -> None:
    dialogos_sincronizacion.show_message_with_details(ventana, title, message, details, icon, action_buttons)

def show_details_dialog(ventana, title: str, details: str) -> None:
    dialogos_sincronizacion.show_details_dialog(ventana, title, details)
