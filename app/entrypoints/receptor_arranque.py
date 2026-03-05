from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, Slot

from app.ui.qt_hilos import obtener_ids_hilos_qt

LOGGER = logging.getLogger(__name__)


class ReceptorArranqueQt(QObject):
    def __init__(self, coordinador, scheduler: Callable[[Callable[[], None]], None] | None = None) -> None:
        super().__init__()
        self._coordinador = coordinador
        self._scheduler = scheduler or self._programar_en_siguiente_tick
        self._callback_finalizacion_pendiente: Callable[[], None] | None = None

    def _programar_en_siguiente_tick(self, callback: Callable[[], None]) -> None:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, callback)

    def _ejecutar_finalizacion_ui(self, resultado: object) -> None:
        try:
            self._coordinador._marcar_boot_stage("receptor_delegate_running")
            self._coordinador.finalizar_arranque_interfaz(resultado)
            self._coordinador._marcar_boot_stage("receptor_after_delegate")
        except Exception:  # noqa: BLE001
            self._coordinador._marcar_boot_stage("receptor_delegate_exception")
            LOGGER.exception(
                "UI_STARTUP_DELEGATE_EXCEPTION",
                extra={"extra": {"codigo": "UI_STARTUP_DELEGATE_EXCEPTION"}},
            )
            self._coordinador._mostrar_fallback_arranque()
        finally:
            self._callback_finalizacion_pendiente = None

    @Slot(object)
    def recibir_ok(self, resultado: object) -> None:
        try:
            self._coordinador._marcar_boot_stage("on_finished_enter_ui")
            LOGGER.info(
                "startup_finished_en_hilo_ui",
                extra={"extra": obtener_ids_hilos_qt()},
            )
            self._coordinador._marcar_boot_stage("receptor_before_delegate")
            def callback() -> None:
                self._ejecutar_finalizacion_ui(resultado)

            self._callback_finalizacion_pendiente = callback
            self._scheduler(callback)
            self._coordinador._marcar_boot_stage("receptor_delegate_scheduled")
        except Exception:  # noqa: BLE001
            self._coordinador._marcar_boot_stage("receptor_delegate_exception")
            LOGGER.exception(
                "UI_STARTUP_DELEGATE_EXCEPTION",
                extra={"extra": {"codigo": "UI_STARTUP_DELEGATE_EXCEPTION"}},
            )
            self._coordinador._mostrar_fallback_arranque()

    @Slot(object)
    def recibir_error(self, error: object) -> None:
        try:
            self._coordinador._marcar_boot_stage("on_failed_enter_ui")
            LOGGER.info(
                "startup_failed_en_hilo_ui",
                extra={"extra": obtener_ids_hilos_qt()},
            )
            self._coordinador._on_failed_ui(error)
        except Exception:  # noqa: BLE001
            self._coordinador._marcar_boot_stage("on_finished_exception_ui")
            LOGGER.exception(
                "UI_STARTUP_FINALIZE_EXCEPTION",
                extra={"extra": {"codigo": "UI_STARTUP_FINALIZE_EXCEPTION"}},
            )
            self._coordinador._mostrar_fallback_arranque()
