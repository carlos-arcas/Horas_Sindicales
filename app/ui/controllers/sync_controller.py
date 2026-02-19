from __future__ import annotations

import traceback
import logging

from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.domain.sync_models import SyncSummary
from app.core.observability import OperationContext, log_event


logger = logging.getLogger(__name__)


class _SyncWorker(QObject):
    finished = Signal(SyncSummary)
    failed = Signal(object)

    def __init__(self, sync_use_case, correlation_id: str) -> None:
        super().__init__()
        self._sync_use_case = sync_use_case
        self._correlation_id = correlation_id

    @Slot()
    def run(self) -> None:
        try:
            log_event(
                logger,
                "sync_started",
                {"operation": "sync_bidirectional"},
                self._correlation_id,
            )
            summary = self._sync_use_case.sync_bidirectional()
            log_event(
                logger,
                "sync_succeeded",
                {
                    "downloaded": summary.downloaded,
                    "uploaded": summary.uploaded,
                    "conflicts": summary.conflicts,
                },
                self._correlation_id,
            )
        except Exception as exc:  # pragma: no cover
            log_event(
                logger,
                "sync_failed",
                {"error": str(exc)},
                self._correlation_id,
            )
            self.failed.emit({"error": exc, "details": traceback.format_exc()})
            return
        self.finished.emit(summary)


class SyncController:
    def __init__(self, window) -> None:
        self.window = window

    def on_sync(self) -> None:
        w = self.window
        if not w._sync_service.is_configured():
            w.toast.warning("No hay configuración de Google Sheets. Abre Opciones para configurarlo.", title="Sin configuración")
            return
        w._set_sync_in_progress(True)
        w._sync_thread = QThread()
        operation_context = OperationContext("sync_ui")
        w._sync_operation_context = operation_context
        w._sync_worker = _SyncWorker(w._sync_service, operation_context.correlation_id)
        w._sync_worker.moveToThread(w._sync_thread)
        w._sync_thread.started.connect(w._sync_worker.run)
        w._sync_worker.finished.connect(w._on_sync_finished)
        w._sync_worker.failed.connect(w._on_sync_failed)
        w._sync_worker.finished.connect(w._sync_thread.quit)
        w._sync_worker.finished.connect(w._sync_worker.deleteLater)
        w._sync_thread.finished.connect(w._sync_thread.deleteLater)
        w._sync_thread.start()

    def update_sync_button_state(self) -> None:
        w = self.window
        configured = w._sync_service.is_configured()
        w.sync_button.setEnabled(configured and not w._sync_in_progress)
        w.review_conflicts_button.setEnabled(not w._sync_in_progress and w._conflicts_service.count_conflicts() > 0)

    def on_open_opciones(self) -> None:
        w = self.window
        from app.ui.dialog_opciones import OpcionesDialog

        dialog = OpcionesDialog(w._sheets_service, w)
        dialog.exec()
        self.update_sync_button_state()
