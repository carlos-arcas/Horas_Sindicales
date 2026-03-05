from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Slot

from app.ui.qt_hilos import obtener_ids_hilos_qt

LOGGER = logging.getLogger(__name__)


class ReceptorArranqueQt(QObject):
    def __init__(self, coordinador) -> None:
        super().__init__()
        self._coordinador = coordinador

    @Slot(object)
    def recibir_ok(self, resultado: object) -> None:
        self._coordinador._marcar_boot_stage("on_finished_enter_ui")
        LOGGER.info(
            "startup_finished_en_hilo_ui",
            extra={"extra": obtener_ids_hilos_qt()},
        )
        self._coordinador._on_finished_ui(resultado)

    @Slot(object)
    def recibir_error(self, error: object) -> None:
        self._coordinador._marcar_boot_stage("on_failed_enter_ui")
        LOGGER.info(
            "startup_failed_en_hilo_ui",
            extra={"extra": obtener_ids_hilos_qt()},
        )
        self._coordinador._on_failed_ui(error)
