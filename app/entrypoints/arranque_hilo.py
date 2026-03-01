from __future__ import annotations

import logging
import sys
import traceback
import uuid
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from app.entrypoints.arranque_nucleo import ejecutar_arranque_puro

LOGGER = logging.getLogger(__name__)


class TrabajadorArranque(QObject):
    progreso = Signal(str)
    finished = Signal(object)
    failed = Signal(str, str, str)

    def __init__(self, container_seed: Any, i18n) -> None:
        super().__init__()
        self._container_seed = container_seed
        self._i18n = i18n

    def _emitir_progreso(self, etapa: str) -> None:
        self.progreso.emit(etapa)

    @Slot()
    def run(self) -> None:
        resultado_emitido = False
        etapa_actual = "bootstrap.container"
        try:
            self._emitir_progreso(etapa_actual)
            etapa_actual = "bootstrap.deps_arranque"
            self._emitir_progreso(etapa_actual)
            from app.entrypoints.ui_main import _construir_dependencias_arranque

            resultado = ejecutar_arranque_puro(
                self._container_seed,
                _construir_dependencias_arranque,
            )

            etapa_actual = "bootstrap.crear_mainwindow_deps"
            self._emitir_progreso(etapa_actual)
            self.finished.emit((resultado.container, resultado.deps_arranque, resultado.idioma))
            resultado_emitido = True
        except Exception as exc:  # noqa: BLE001
            incident_id = f"INC-BOOT-{uuid.uuid4().hex[:12].upper()}"
            detalles = "".join(traceback.format_exception(*sys.exc_info()))
            LOGGER.exception(
                "STARTUP_WORKER_FAILED",
                extra={"extra": {"incident_id": incident_id, "etapa": etapa_actual}},
            )
            self.failed.emit(
                incident_id,
                self._i18n.t("startup_error_dialog_message"),
                detalles or repr(exc),
            )
            resultado_emitido = True
        finally:
            if not resultado_emitido:
                incident_id = f"INC-BOOT-{uuid.uuid4().hex[:12].upper()}"
                detalles = self._i18n.t("startup_worker_no_terminal_signal", etapa=etapa_actual)
                LOGGER.error(
                    "STARTUP_WORKER_NO_TERMINAL_SIGNAL",
                    extra={"extra": {"incident_id": incident_id, "etapa": etapa_actual}},
                )
                self.failed.emit(
                    incident_id,
                    self._i18n.t("startup_error_dialog_message"),
                    detalles,
                )
