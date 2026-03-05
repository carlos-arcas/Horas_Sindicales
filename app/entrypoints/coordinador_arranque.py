from __future__ import annotations

import logging
import sys
import time
from typing import Callable

from aplicacion.casos_de_uso.onboarding import ReiniciarOnboarding
from app.bootstrap.captura_fallos_fatales import marcar_stage
from app.entrypoints.arranque_nucleo import ResultadoArranque
from app.entrypoints.startup_watchdog import calcular_elapsed_ms

from PySide6.QtCore import QObject, QTimer, Slot

from app.ui.qt_safe_ops import es_objeto_qt_valido, safe_hide, safe_quit_thread

LOGGER = logging.getLogger(__name__)


class CoordinadorArranque(QObject):
    def __init__(
        self,
        *,
        app,
        i18n,
        splash,
        startup_timeout_ms: int,
        startup_thread,
        startup_worker,
        watchdog_timer,
        main_window_factory: Callable[..., object],
        orquestador_factory: Callable[..., object],
        instalar_menu_ayuda: Callable[..., None],
        fallo_arranque_handler: Callable[..., str],
    ) -> None:
        super().__init__()
        self.app = app
        self.i18n = i18n
        self.splash = splash
        self.startup_timeout_ms = startup_timeout_ms
        self.thread = startup_thread
        self.worker = startup_worker
        self.watchdog_timer = watchdog_timer
        self.main_window_factory = main_window_factory
        self.orquestador_factory = orquestador_factory
        self.instalar_menu_ayuda = instalar_menu_ayuda
        self.fallo_arranque_handler = fallo_arranque_handler
        self.incident_id = ""
        self.ultima_etapa = ""
        self.terminado = False
        self.watchdog_disparado = False
        self._fallo_arranque_reportado = False
        self._splash_cerrado = False
        self._boot_finalizado = False
        self._boot_timeout_disparado = False
        self._boot_inicio_monotonic = time.monotonic()
        self._timer_watchdog = watchdog_timer

    def iniciar(self) -> None:
        self._boot_inicio_monotonic = time.monotonic()
        self._timer_watchdog = self.watchdog_timer
        self.watchdog_timer.start()

    def _marcar_boot_stage(self, stage: str) -> None:
        self.ultima_etapa = stage
        marcar_stage(stage)

    def _qt_is_alive(self, obj) -> bool:
        return es_objeto_qt_valido(obj)

    def _detalles_con_etapa(self, detalles: str) -> str:
        if not self.ultima_etapa:
            return detalles
        etiqueta = self.i18n.t(
            "startup_last_stage", etapa=self.i18n.t(self.ultima_etapa)
        )
        if not detalles:
            return etiqueta
        return f"{etiqueta}\n{detalles}"

    def _detener_watchdog_idempotente(self) -> None:
        if not self._qt_is_alive(self._timer_watchdog):
            return
        try:
            self._timer_watchdog.stop()
        except RuntimeError:
            return

    def _cerrar_splash_idempotente(self) -> None:
        if self._splash_cerrado:
            return
        self._splash_cerrado = True
        safe_hide(self.splash)

    def _solicitar_cierre_thread(self) -> None:
        safe_quit_thread(self.thread)

    def _reportar_fallo_arranque(self, **kwargs) -> None:
        if self._fallo_arranque_reportado:
            return
        self._fallo_arranque_reportado = True
        self.fallo_arranque_handler(**kwargs)

    def _finalizar_arranque(self) -> None:
        self._boot_finalizado = True
        self.terminado = True
        self._detener_watchdog_idempotente()

    def _evento_finish_tardio(self, evento: str) -> None:
        LOGGER.warning(
            "UI_STARTUP_FINISHED_AFTER_TIMEOUT",
            extra={"extra": {"evento": evento, "ultima_etapa": self.ultima_etapa, "decision": "ignore"}},
        )

    @Slot(str)
    def on_progreso(self, etapa: str) -> None:
        self._marcar_boot_stage(etapa)
        if self._qt_is_alive(self.splash):
            self.splash.set_status(etapa)

    @Slot()
    def on_timeout(self) -> None:
        self._on_startup_timeout()

    def _on_startup_timeout(self) -> None:
        if self._boot_finalizado:
            return
        self.watchdog_disparado = True
        self._boot_timeout_disparado = True
        if not self.incident_id:
            import uuid

            self.incident_id = f"INC-UI-{uuid.uuid4().hex[:12].upper()}"
        elapsed_ms = calcular_elapsed_ms(self._boot_inicio_monotonic, time.monotonic())
        self._marcar_boot_stage("startup_timeout")
        LOGGER.error(
            "UI_STARTUP_TIMEOUT",
            extra={
                "extra": {
                    "incident_id": self.incident_id,
                    "ultima_etapa": self.ultima_etapa,
                    "timeout_ms": self.startup_timeout_ms,
                    "elapsed_ms": elapsed_ms,
                }
            },
        )
        self._finalizar_arranque()
        self._cerrar_splash_idempotente()
        self._solicitar_cierre_thread()
        self._reportar_fallo_arranque(
            exc=None,
            trace_info=None,
            i18n=self.i18n,
            splash=self.splash,
            startup_thread=self.thread,
            app=self.app,
            mensaje_usuario="startup_timeout_title",
            incident_id=self.incident_id,
            detalles=self._detalles_con_etapa(self.i18n.t("startup_timeout_message")),
            watchdog_timer=self._timer_watchdog,
        )

    @Slot(object)
    def on_finished(self, startup_payload: ResultadoArranque) -> None:
        if self._boot_timeout_disparado:
            self._evento_finish_tardio("finished")
            return
        self.terminado = True

        def _aplicar_resultado_ui() -> None:
            self._detener_watchdog_idempotente()
            self._cerrar_splash_idempotente()
            self._solicitar_cierre_thread()
            resolved_container = startup_payload.container
            deps_arranque = startup_payload.deps_arranque
            idioma = startup_payload.idioma
            self.i18n.set_idioma(idioma)
            orquestador = self.orquestador_factory(deps_arranque, self.i18n)
            if not orquestador.resolver_onboarding():
                self._finalizar_arranque()
                self.app.exit(0)
                return
            window = self.main_window_factory(
                resolved_container,
                deps_arranque,
            )
            self.app.setProperty("_main_window_ref", window)
            self.instalar_menu_ayuda(
                window,
                self.i18n,
                ReiniciarOnboarding(resolved_container.repositorio_preferencias),
                resolved_container.cargar_datos_demo_caso_uso,
            )
            if orquestador.debe_iniciar_maximizada():
                window.showMaximized()
            else:
                window.show()
            self._finalizar_arranque()

        try:
            QTimer.singleShot(0, _aplicar_resultado_ui)
        except Exception as exc:  # noqa: BLE001
            self._reportar_fallo_arranque(
                exc=exc,
                trace_info=sys.exc_info(),
                i18n=self.i18n,
                splash=self.splash,
                startup_thread=self.thread,
                app=self.app,
                watchdog_timer=self._timer_watchdog,
            )

    @Slot(str, str, str)
    def on_failed(self, incident_id: str, mensaje_usuario: str, detalles: str) -> None:
        if self._boot_timeout_disparado:
            self._evento_finish_tardio("failed")
            return
        self.terminado = True
        self.incident_id = incident_id
        mensaje_ui = self.i18n.t(mensaje_usuario)
        detalles_ui = detalles
        if detalles.startswith("startup_worker_no_terminal_signal:"):
            etapa = detalles.split(":", maxsplit=1)[1]
            detalles_ui = self.i18n.t("startup_worker_no_terminal_signal", etapa=etapa)

        def _fallar_en_ui() -> None:
            self._finalizar_arranque()
            self._cerrar_splash_idempotente()
            self._solicitar_cierre_thread()
            self._reportar_fallo_arranque(
                exc=None,
                trace_info=None,
                i18n=self.i18n,
                splash=self.splash,
                startup_thread=self.thread,
                app=self.app,
                mensaje_usuario=mensaje_ui,
                dialogo_factory=None,
                incident_id=incident_id,
                detalles=self._detalles_con_etapa(detalles_ui),
                watchdog_timer=self._timer_watchdog,
            )

        QTimer.singleShot(0, _fallar_en_ui)
