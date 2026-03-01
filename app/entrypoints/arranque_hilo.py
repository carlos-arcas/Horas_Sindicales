from __future__ import annotations

import logging
import sys
import traceback
import uuid
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from app.application.dto import FalloArranqueDatos
from app.entrypoints.arranque_nucleo import ejecutar_arranque_puro

LOGGER = logging.getLogger(__name__)


class TrabajadorArranque(QObject):
    progreso = Signal(str)
    finished = Signal(object)
    failed = Signal(str, str, str)
    error_ocurrido = Signal(object)

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
            self.finished.emit(
                (resultado.container, resultado.deps_arranque, resultado.idioma)
            )
            resultado_emitido = True
        except Exception as exc:  # noqa: BLE001
            incident_id = f"INC-BOOT-{uuid.uuid4().hex[:12].upper()}"
            detalles = "".join(traceback.format_exception(*sys.exc_info()))
            dto = FalloArranqueDatos(
                incident_id=incident_id,
                tipo_error=type(exc).__name__,
                mensaje_error=str(exc),
                traceback_error=detalles or repr(exc),
                mensaje_usuario=self._i18n.t("startup_error_dialog_message"),
                etapa=etapa_actual,
            )
            LOGGER.exception(
                "STARTUP_WORKER_FAILED",
                extra={"extra": {"incident_id": incident_id, "etapa": etapa_actual}},
            )
            self.error_ocurrido.emit(dto)
            self.failed.emit(
                incident_id,
                dto.mensaje_usuario,
                dto.traceback_error,
            )
            resultado_emitido = True
        finally:
            if not resultado_emitido:
                incident_id = f"INC-BOOT-{uuid.uuid4().hex[:12].upper()}"
                detalles = self._i18n.t(
                    "startup_worker_no_terminal_signal", etapa=etapa_actual
                )
                LOGGER.error(
                    "STARTUP_WORKER_NO_TERMINAL_SIGNAL",
                    extra={
                        "extra": {"incident_id": incident_id, "etapa": etapa_actual}
                    },
                )
                self.failed.emit(
                    incident_id,
                    self._i18n.t("startup_error_dialog_message"),
                    detalles,
                )
