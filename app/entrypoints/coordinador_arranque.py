from __future__ import annotations

import logging
import sys
from typing import Callable

from aplicacion.casos_de_uso.onboarding import ReiniciarOnboarding

from PySide6.QtCore import QObject, Slot

LOGGER = logging.getLogger(__name__)


class CoordinadorArranque(QObject):
    def __init__(
        self,
        *,
        app,
        i18n,
        splash,
        startup_timeout_ms: int,
        container_seed=None,
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
        self.container_seed = container_seed
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

    def iniciar(self) -> None:
        self.watchdog_timer.start()

    def _qt_is_alive(self, obj) -> bool:
        if obj is None:
            return False
        try:
            from shiboken6 import isValid

            return bool(isValid(obj))
        except Exception:
            try:
                return bool(obj)
            except RuntimeError:
                return False

    def _detalles_con_etapa(self, detalles: str) -> str:
        if not self.ultima_etapa:
            return detalles
        etiqueta = self.i18n.t("startup_last_stage", etapa=self.i18n.t(self.ultima_etapa))
        if not detalles:
            return etiqueta
        return f"{etiqueta}\n{detalles}"

    def _detener_watchdog_idempotente(self) -> None:
        if not self._qt_is_alive(self.watchdog_timer):
            return
        try:
            self.watchdog_timer.stop()
        except RuntimeError:
            return

    def _cerrar_splash_idempotente(self) -> None:
        if self._splash_cerrado:
            return
        self._splash_cerrado = True
        if not self._qt_is_alive(self.splash):
            return
        try:
            if hasattr(self.splash, "request_close"):
                self.splash.request_close()
            else:
                self.splash.hide()
                self.splash.close()
        except RuntimeError:
            return

    def _solicitar_cierre_thread(self) -> None:
        if not self._qt_is_alive(self.thread) or not hasattr(self.thread, "quit"):
            return
        try:
            self.thread.quit()
        except RuntimeError:
            return

    def _reportar_fallo_arranque(self, **kwargs) -> None:
        if self._fallo_arranque_reportado:
            return
        self._fallo_arranque_reportado = True
        self.fallo_arranque_handler(**kwargs)

    @Slot(str)
    def on_progreso(self, etapa: str) -> None:
        self.ultima_etapa = etapa
        if self._qt_is_alive(self.splash):
            self.splash.set_status(etapa)

    @Slot()
    def on_timeout(self) -> None:
        if self.terminado:
            return
        self.watchdog_disparado = True
        self.terminado = True
        if not self.incident_id:
            import uuid

            self.incident_id = f"INC-UI-{uuid.uuid4().hex[:12].upper()}"
        LOGGER.warning(
            "STARTUP_TIMEOUT",
            extra={
                "extra": {
                    "incident_id": self.incident_id,
                    "etapa": self.ultima_etapa,
                    "timeout_ms": self.startup_timeout_ms,
                }
            },
        )
        self._detener_watchdog_idempotente()
        self._cerrar_splash_idempotente()
        self._solicitar_cierre_thread()
        self._reportar_fallo_arranque(
            exc=None,
            trace_info=None,
            i18n=self.i18n,
            splash=self.splash,
            startup_thread=self.thread,
            app=self.app,
            mensaje_usuario=self.i18n.t("startup_timeout_message"),
            incident_id=self.incident_id,
            detalles=self._detalles_con_etapa(self.i18n.t("startup_timeout_message")),
            watchdog_timer=self.watchdog_timer,
        )

    @Slot(object)
    def on_finished(self, startup_payload) -> None:
        self.terminado = True
        try:
            self._detener_watchdog_idempotente()
            self._cerrar_splash_idempotente()
            self._solicitar_cierre_thread()
            resolved_container, deps_arranque, idioma = startup_payload
            self.i18n.set_idioma(idioma)
            orquestador = self.orquestador_factory(deps_arranque, self.i18n)
            if not orquestador.resolver_onboarding():
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
        except Exception as exc:  # noqa: BLE001
            self._reportar_fallo_arranque(
                exc=exc,
                trace_info=sys.exc_info(),
                i18n=self.i18n,
                splash=self.splash,
                startup_thread=self.thread,
                app=self.app,
                watchdog_timer=self.watchdog_timer,
            )

    @Slot(str, str, str)
    def on_failed(self, incident_id: str, mensaje_usuario: str, detalles: str) -> None:
        self.terminado = True
        self.incident_id = incident_id
        self._detener_watchdog_idempotente()
        self._cerrar_splash_idempotente()
        self._solicitar_cierre_thread()
        self._reportar_fallo_arranque(
            exc=None,
            trace_info=None,
            i18n=self.i18n,
            splash=self.splash,
            startup_thread=self.thread,
            app=self.app,
            mensaje_usuario=mensaje_usuario,
            dialogo_factory=None,
            incident_id=incident_id,
            detalles=self._detalles_con_etapa(detalles),
            watchdog_timer=self.watchdog_timer,
        )
