from __future__ import annotations

import logging
import sys
import traceback
import uuid
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from app.entrypoints.arranque_nucleo import planificar_arranque_core

LOGGER = logging.getLogger(__name__)


class TrabajadorArranque(QObject):
    progreso = Signal(str)
    finished = Signal(object)
    failed = Signal(str, str, str)

    def __init__(self, container_seed: Any) -> None:
        super().__init__()
        self._container_seed = container_seed

    def _emitir_progreso(self, etapa: str) -> None:
        self.progreso.emit(etapa)

    @Slot()
    def run(self) -> None:
        resultado_emitido = False
        etapa_actual = "bootstrap.container"
        try:
            self._emitir_progreso(etapa_actual)
            etapa_actual = "bootstrap.core_ready"
            self._emitir_progreso(etapa_actual)
            resultado = planificar_arranque_core(self._container_seed)
            self._emitir_progreso("on_finished_signal_received")
            LOGGER.info(
                "startup_finished_signal_received",
                extra={"extra": {"BOOT_STAGE": "on_finished_signal_received"}},
            )
            self.finished.emit(resultado)
            resultado_emitido = True
        except Exception as exc:  # noqa: BLE001
            incident_id = f"INC-BOOT-{uuid.uuid4().hex[:12].upper()}"
            detalles = "".join(traceback.format_exception(*sys.exc_info()))
            LOGGER.exception(
                "STARTUP_WORKER_FAILED",
                extra={"extra": {"incident_id": incident_id, "etapa": etapa_actual}},
            )
            self._emitir_progreso("on_failed_signal_received")
            self.failed.emit(
                incident_id,
                "startup_error_dialog_message",
                detalles or repr(exc),
            )
            resultado_emitido = True
        finally:
            if not resultado_emitido:
                incident_id = f"INC-BOOT-{uuid.uuid4().hex[:12].upper()}"
                LOGGER.error(
                    "STARTUP_WORKER_NO_TERMINAL_SIGNAL",
                    extra={
                        "extra": {"incident_id": incident_id, "etapa": etapa_actual}
                    },
                )
                self.failed.emit(
                    incident_id,
                    "startup_error_dialog_message",
                    f"startup_worker_no_terminal_signal:{etapa_actual}",
                )
