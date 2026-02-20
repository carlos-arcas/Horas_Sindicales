from __future__ import annotations

import traceback
import logging

from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.core.observability import OperationContext, log_event


logger = logging.getLogger(__name__)


class _SyncWorker(QObject):
    finished = Signal(object)
    failed = Signal(object)

    def __init__(self, operation, correlation_id: str, operation_name: str) -> None:
        super().__init__()
        self._operation = operation
        self._correlation_id = correlation_id
        self._operation_name = operation_name

    @Slot()
    def run(self) -> None:
        try:
            log_event(logger, "sync_started", {"operation": self._operation_name}, self._correlation_id)
            result = self._operation()
            log_event(logger, "sync_succeeded", {"operation": self._operation_name}, self._correlation_id)
        except Exception as exc:  # pragma: no cover
            log_event(logger, "sync_failed", {"operation": self._operation_name, "error": str(exc)}, self._correlation_id)
            self.failed.emit({"error": exc, "details": traceback.format_exc()})
            return
        self.finished.emit(result)


class SyncController:
    def __init__(self, window) -> None:
        self.window = window

    def on_sync(self) -> None:
        self._run_background_operation(
            operation=lambda: self.window._sync_service.sync_bidirectional(),
            on_finished=getattr(self.window, "_on_sync_finished", lambda *_: None),
            operation_name="sync_bidirectional",
        )

    def on_simulate_sync(self) -> None:
        self._run_background_operation(
            operation=lambda: self.window._sync_service.simulate_sync_plan(),
            on_finished=getattr(self.window, "_on_sync_simulation_finished", lambda *_: None),
            operation_name="simulate_sync",
        )

    def on_confirm_sync(self) -> None:
        w = self.window
        if w._pending_sync_plan is None:
            w.toast.warning("Primero ejecuta una simulación para generar el plan.", title="Sin plan")
            return
        if not w._pending_sync_plan.has_changes:
            w.toast.info("No hay cambios que aplicar", title="Sincronización")
            return
        self._run_background_operation(
            operation=lambda: w._sync_service.execute_sync_plan(w._pending_sync_plan),
            on_finished=getattr(w, "_on_sync_finished", lambda *_: None),
            operation_name="execute_sync_plan",
        )

    def _run_background_operation(self, *, operation, on_finished, operation_name: str) -> None:
        w = self.window
        if w._sync_in_progress:
            return
        if not w._sync_service.is_configured():
            w._set_config_incomplete_state()
            w.toast.warning("No hay configuración de Google Sheets. Abre Opciones para configurarlo.", title="Sin configuración")
            return
        w._set_sync_in_progress(True)
        w._sync_thread = QThread()
        operation_context = OperationContext("sync_ui")
        w._sync_operation_context = operation_context
        w._sync_worker = _SyncWorker(operation, operation_context.correlation_id, operation_name)
        w._sync_worker.moveToThread(w._sync_thread)
        w._sync_thread.started.connect(w._sync_worker.run)
        w._sync_worker.finished.connect(on_finished)
        w._sync_worker.failed.connect(w._on_sync_failed)
        w._sync_worker.finished.connect(w._sync_thread.quit)
        w._sync_worker.finished.connect(w._sync_worker.deleteLater)
        w._sync_thread.finished.connect(w._sync_thread.deleteLater)
        w._sync_thread.start()

    def update_sync_button_state(self) -> None:
        w = self.window
        configured = w._sync_service.is_configured()
        enabled = configured and not w._sync_in_progress
        w.sync_button.setEnabled(enabled)
        if hasattr(w, "simulate_sync_button"):
            w.simulate_sync_button.setEnabled(enabled)
        if hasattr(w, "confirm_sync_button"):
            pending_plan = getattr(w, "_pending_sync_plan", None)
            has_plan_changes = bool(pending_plan is not None and pending_plan.has_changes)
            has_unresolved_conflicts = bool(pending_plan is not None and pending_plan.conflicts)
            w.confirm_sync_button.setEnabled(enabled and has_plan_changes and not has_unresolved_conflicts)
        if hasattr(w, "retry_failed_button"):
            report = getattr(w, "_last_sync_report", None)
            has_failures = bool(report and (report.errors or report.conflicts))
            w.retry_failed_button.setEnabled(not w._sync_in_progress and has_failures)
        conflicts_total = w._conflicts_service.count_conflicts()
        w.review_conflicts_button.setText("Ver conflictos" if conflicts_total > 0 else "Ver conflictos (sin pendientes)")
        w.review_conflicts_button.setEnabled(not w._sync_in_progress and conflicts_total > 0)
        if hasattr(w, "sync_details_button"):
            w.sync_details_button.setEnabled(not w._sync_in_progress and w._last_sync_report is not None)
        if hasattr(w, "copy_sync_report_button"):
            w.copy_sync_report_button.setEnabled(not w._sync_in_progress and w._last_sync_report is not None)

    def on_open_opciones(self) -> None:
        w = self.window
        from app.ui.dialog_opciones import OpcionesDialog

        dialog = OpcionesDialog(w._sheets_service, w)
        dialog.exec()
        if w._sync_service.is_configured():
            w.go_to_sync_config_button.setVisible(False)
            w._set_sync_status_badge("IDLE")
            w.sync_panel_status.setText("Detalle: Sistema en espera.")
        self.update_sync_button_state()
