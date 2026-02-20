from __future__ import annotations

import logging
import traceback

from PySide6.QtCore import QObject, Signal, Slot

from app.application.sync_sheets_use_case import SyncSheetsUseCase
from app.domain.sync_models import SyncSummary

logger = logging.getLogger(__name__)


class SyncWorker(QObject):
    finished = Signal(SyncSummary)
    failed = Signal(object)

    def __init__(self, sync_use_case: SyncSheetsUseCase) -> None:
        super().__init__()
        self._sync_use_case = sync_use_case

    @Slot()
    def run(self) -> None:
        try:
            summary = self._sync_use_case.sync_bidirectional()
        except Exception as exc:
            logger.exception("Error durante la sincronización")
            self.failed.emit({"error": exc, "details": traceback.format_exc()})
            return
        self.finished.emit(summary)


class PushWorker(QObject):
    finished = Signal(SyncSummary)
    failed = Signal(object)

    def __init__(self, sync_use_case: SyncSheetsUseCase) -> None:
        super().__init__()
        self._sync_use_case = sync_use_case

    @Slot()
    def run(self) -> None:
        try:
            summary = self._sync_use_case.push()
        except Exception as exc:
            logger.exception("Error durante la subida")
            self.failed.emit({"error": exc, "details": traceback.format_exc()})
            return
        self.finished.emit(summary)
