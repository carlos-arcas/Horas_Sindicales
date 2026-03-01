from __future__ import annotations

import logging
import sys
import traceback
import uuid
from types import TracebackType
from typing import Callable

from aplicacion.casos_de_uso.documentos import ObtenerRutaGuiaSync
from aplicacion.casos_de_uso.idioma import GuardarIdiomaUI, ObtenerIdiomaUI
from aplicacion.casos_de_uso.onboarding import MarcarOnboardingCompletado, ObtenerEstadoOnboarding, ReiniciarOnboarding
from aplicacion.casos_de_uso.preferencia_pantalla_completa import (
    GuardarPreferenciaPantallaCompleta,
    ObtenerPreferenciaPantallaCompleta,
)
from app.application.use_cases.cargar_datos_demo_caso_uso import CargarDatosDemoCasoUso
from app.bootstrap.exception_handler import manejar_excepcion_global
from app.bootstrap.logging import log_operational_error

LOGGER = logging.getLogger(__name__)


def _resolver_startup_timeout_ms() -> int:
    import os

    raw = os.getenv("HORAS_STARTUP_TIMEOUT_MS", "25000")
    try:
        return max(1, int(raw))
    except ValueError:
        return 25_000


def construir_mensaje_error_ui(incident_id: str) -> str:
    return f"Ha ocurrido un error inesperado.\nID de incidente: {incident_id}"


def manejar_excepcion_ui(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType,
) -> str:
    incident_id = manejar_excepcion_global(exc_type, exc_value, exc_traceback)
    from PySide6.QtWidgets import QApplication, QMessageBox

    app = QApplication.instance()
    if app is None:
        return incident_id
    try:
        QMessageBox.critical(None, "Error inesperado", construir_mensaje_error_ui(incident_id))
    except Exception:
        pass
    return incident_id


def _resolver_incident_id(exc: Exception | None, trace_info) -> str:
    if trace_info is not None and all(trace_info):
        return manejar_excepcion_ui(trace_info[0], trace_info[1], trace_info[2])
    incident_id = f"INC-UI-{uuid.uuid4().hex[:12].upper()}"
    log_operational_error(
        LOGGER,
        "Fallo de arranque sin traceback tipado",
        exc=exc,
        extra={"incident_id": incident_id},
    )
    return incident_id


def _manejar_fallo_arranque(
    *,
    exc: Exception | None,
    trace_info,
    i18n,
    splash,
    startup_thread,
    app,
    dialogo_factory: Callable[..., object] | None = None,
    mensaje_usuario: str | None = None,
    incident_id: str | None = None,
    detalles: str | None = None,
    watchdog_timer=None,
) -> str:
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtWidgets import QApplication

    try:
        from shiboken6 import isValid as _is_valid_qobject
    except Exception:  # pragma: no cover - fallback defensivo
        _is_valid_qobject = None

    def _cerrar_splash() -> None:
        if splash is None:
            return
        splash.hide()
        splash.close()
        QTimer.singleShot(0, splash.deleteLater)

    def _safe_quit_thread() -> None:
        if startup_thread is None or not hasattr(startup_thread, "quit"):
            return
        if _is_valid_qobject is not None and not _is_valid_qobject(startup_thread):
            return
        try:
            startup_thread.quit()
        except RuntimeError as exc:
            LOGGER.warning("STARTUP_THREAD_ALREADY_DESTROYED", exc_info=exc)

    resolved_incident_id = incident_id or _resolver_incident_id(exc, trace_info)
    resolved_detalles = detalles or ""
    if not resolved_detalles:
        if trace_info is not None and all(trace_info):
            resolved_detalles = "".join(traceback.format_exception(trace_info[0], trace_info[1], trace_info[2]))
        elif exc is not None:
            resolved_detalles = repr(exc)

    log_operational_error(
        LOGGER,
        i18n.t("splash_error_mensaje", incident_id=resolved_incident_id),
        exc=exc,
        extra={"incident_id": resolved_incident_id},
    )
    if watchdog_timer is not None and hasattr(watchdog_timer, "stop"):
        watchdog_timer.stop()
    _safe_quit_thread()
    _cerrar_splash()

    if dialogo_factory is None:
        from app.ui.dialogos.dialogo_error_arranque import DialogoErrorArranque

        dialogo_factory = DialogoErrorArranque

    dialogo = dialogo_factory(
        i18n,
        titulo=i18n.t("splash_error_titulo"),
        mensaje_usuario=mensaje_usuario or i18n.t("startup_error_dialog_message"),
        incident_id=resolved_incident_id,
        detalles=resolved_detalles,
        parent=None,
    )

    def _exit_con_codigo() -> None:
        QTimer.singleShot(0, lambda: QApplication.exit(2))

    if hasattr(dialogo, "setWindowModality"):
        dialogo.setWindowModality(Qt.ApplicationModal)
    if hasattr(dialogo, "setWindowFlag"):
        dialogo.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    if hasattr(dialogo, "finished"):
        dialogo.finished.connect(_exit_con_codigo)
    if hasattr(dialogo, "show"):
        dialogo.show()
    if hasattr(dialogo, "raise_"):
        dialogo.raise_()
    if hasattr(dialogo, "activateWindow"):
        dialogo.activateWindow()
    if not hasattr(dialogo, "finished") and hasattr(dialogo, "exec"):
        dialogo.exec()
        _exit_con_codigo()
    return resolved_incident_id


def _construir_dependencias_arranque(container):
    from infraestructura.proveedor_documentos import ProveedorDocumentosInfra
    from presentacion.orquestador_arranque import DependenciasArranque

    repo_pref = container.repositorio_preferencias
    proveedor_documentos = ProveedorDocumentosInfra()
    return DependenciasArranque(
        obtener_estado_onboarding=ObtenerEstadoOnboarding(repo_pref),
        marcar_onboarding_completado=MarcarOnboardingCompletado(repo_pref),
        guardar_preferencia_pantalla_completa=GuardarPreferenciaPantallaCompleta(repo_pref),
        obtener_preferencia_pantalla_completa=ObtenerPreferenciaPantallaCompleta(repo_pref),
        obtener_idioma_ui=ObtenerIdiomaUI(repo_pref),
        guardar_idioma_ui=GuardarIdiomaUI(repo_pref),
        obtener_ruta_guia_sync=ObtenerRutaGuiaSync(proveedor_documentos),
    )


def _instalar_menu_ayuda(
    main_window,
    i18n,
    reiniciar_onboarding: ReiniciarOnboarding,
    cargar_datos_demo: CargarDatosDemoCasoUso,
) -> None:
    from PySide6.QtWidgets import QMessageBox

    menu_ayuda = main_window.menuBar().addMenu(i18n.t("menu_ayuda"))
    accion_reiniciar = menu_ayuda.addAction(i18n.t("menu_reiniciar_asistente"))
    accion_cargar_demo = menu_ayuda.addAction(i18n.t("menu_cargar_demo"))

    def _reiniciar_asistente() -> None:
        respuesta = QMessageBox.question(
            main_window,
            i18n.t("menu_reiniciar_confirmar_titulo"),
            i18n.t("menu_reiniciar_confirmar_mensaje"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return
        reiniciar_onboarding.ejecutar()
        QMessageBox.information(main_window, i18n.t("menu_ayuda"), i18n.t("menu_reiniciar_ok"))

    def _cargar_demo() -> None:
        confirmacion = QMessageBox.question(
            main_window,
            i18n.t("menu_cargar_demo_confirmar_titulo"),
            i18n.t("menu_cargar_demo_confirmar_mensaje"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return
        resultado = cargar_datos_demo.ejecutar(modo="BACKUP")
        if resultado.ok:
            main_window._load_personas()
            main_window._reload_pending_views()
            main_window._refresh_historico(force=True)
            main_window._refresh_saldos()
            main_window.main_tabs.setCurrentIndex(0)
            main_window.toast.show(
                i18n.t("menu_cargar_demo_toast_ok"),
                level="success",
                title=i18n.t("menu_cargar_demo"),
                action_label=i18n.t("menu_cargar_demo_ir_solicitudes"),
                action_callback=lambda: main_window.main_tabs.setCurrentIndex(0),
            )
            return
        correlation_id = str(uuid.uuid4())
        main_window.toast.show(
            i18n.t("menu_cargar_demo_toast_error"),
            level="error",
            title=i18n.t("menu_cargar_demo"),
            action_label=i18n.t("menu_cargar_demo_ver_detalles"),
            action_callback=lambda: QMessageBox.critical(
                main_window,
                i18n.t("menu_cargar_demo"),
                resultado.detalles or i18n.t("menu_cargar_demo_error_sin_detalles"),
            ),
            details=resultado.detalles,
            correlation_id=correlation_id,
            code="DEMO_LOAD_FAILED",
        )

    accion_reiniciar.triggered.connect(_reiniciar_asistente)
    accion_cargar_demo.triggered.connect(_cargar_demo)


def run_ui(container=None) -> int:
    from app.entrypoints.arranque_hilo import TrabajadorArranque
    from app.ui.estilos.apply_theme import aplicar_tema
    from app.ui.main_window import MainWindow
    from app.ui.splash_window import SplashWindow
    from app.ui.theme import build_stylesheet
    from presentacion.i18n import I18nManager
    from presentacion.orquestador_arranque import OrquestadorArranqueUI

    from PySide6.QtCore import QObject, QThread, QTimer, Qt, Slot
    from PySide6.QtWidgets import QApplication

    class ControladorArranque(QObject):
        def __init__(self, *, app, i18n, splash, startup_timeout_ms: int, startup_thread, startup_worker) -> None:
            super().__init__()
            self.app = app
            self.i18n = i18n
            self.splash = splash
            self.startup_timeout_ms = startup_timeout_ms
            self.thread = startup_thread
            self.worker = startup_worker
            self.watchdog_timer = QTimer(self)
            self.watchdog_timer.setSingleShot(True)
            self.watchdog_timer.setInterval(startup_timeout_ms)
            self.incident_id = ""
            self.ultima_etapa = ""
            self.terminado = False
            self.watchdog_disparado = False

        def _cerrar_splash(self) -> None:
            self.splash.hide()
            self.splash.close()
            QTimer.singleShot(0, self.splash.deleteLater)

        def _detalles_con_etapa(self, detalles: str) -> str:
            if not self.ultima_etapa:
                return detalles
            etiqueta = self.i18n.t("startup_last_stage", etapa=self.i18n.t(self.ultima_etapa))
            return f"{etiqueta}\n{detalles}" if detalles else etiqueta

        def iniciar(self) -> None:
            self.watchdog_timer.start()

        @Slot(str)
        def on_progreso(self, etapa: str) -> None:
            self.ultima_etapa = etapa
            self.splash.set_status(etapa)

        @Slot()
        def on_timeout(self) -> None:
            if self.terminado:
                return
            self.watchdog_disparado = True
            self.terminado = True
            if not self.incident_id:
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
            _manejar_fallo_arranque(
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
            if __debug__:
                app_thread = QApplication.instance().thread()
                assert QThread.currentThread() == app_thread
            try:
                self.terminado = True
                self.watchdog_timer.stop()
                resolved_container, deps_arranque, idioma = startup_payload
                self.i18n.set_idioma(idioma)
                orquestador = OrquestadorArranqueUI(deps_arranque, self.i18n)
                self._cerrar_splash()

                if not orquestador.resolver_onboarding():
                    self.app.exit(0)
                    return

                window = MainWindow(
                    resolved_container.persona_use_cases,
                    resolved_container.solicitud_use_cases,
                    resolved_container.grupo_use_cases,
                    resolved_container.sheets_service,
                    resolved_container.sync_service,
                    resolved_container.conflicts_service,
                    resolved_container.health_check_use_case,
                    resolved_container.alert_engine,
                    resolved_container.validacion_preventiva_lock_use_case,
                    guardar_preferencia_pantalla_completa=deps_arranque.guardar_preferencia_pantalla_completa,
                    obtener_preferencia_pantalla_completa=deps_arranque.obtener_preferencia_pantalla_completa,
                )
                self.app.setProperty("_main_window_ref", window)
                _instalar_menu_ayuda(
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
                exc_type, exc_value, exc_traceback = sys.exc_info()
                _manejar_fallo_arranque(
                    exc=exc,
                    trace_info=(exc_type, exc_value, exc_traceback),
                    i18n=self.i18n,
                    splash=self.splash,
                    startup_thread=self.thread,
                    app=self.app,
                    watchdog_timer=self.watchdog_timer,
                )

        @Slot(str, str, str)
        def on_failed(self, incident_id: str, mensaje_usuario: str, detalles: str) -> None:
            self.terminado = True
            self.watchdog_timer.stop()
            self.incident_id = incident_id
            self._cerrar_splash()
            _manejar_fallo_arranque(
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

    startup_timeout_ms = _resolver_startup_timeout_ms()

    app = QApplication([])
    i18n = I18nManager("es")
    splash = SplashWindow(i18n)
    splash.show()

    startup_thread = QThread()
    startup_worker = TrabajadorArranque(container, i18n)
    startup_worker.moveToThread(startup_thread)
    splash.registrar_arranque(startup_thread, startup_worker)

    controlador = ControladorArranque(
        app=app,
        i18n=i18n,
        splash=splash,
        startup_timeout_ms=startup_timeout_ms,
        startup_thread=startup_thread,
        startup_worker=startup_worker,
    )

    controlador.watchdog_timer.timeout.connect(controlador.on_timeout, Qt.ConnectionType.QueuedConnection)
    startup_worker.finished.connect(startup_thread.quit)
    startup_worker.progreso.connect(controlador.on_progreso, Qt.ConnectionType.QueuedConnection)
    startup_worker.finished.connect(controlador.on_finished, Qt.ConnectionType.QueuedConnection)
    startup_worker.failed.connect(startup_thread.quit)
    startup_worker.failed.connect(controlador.on_failed, Qt.ConnectionType.QueuedConnection)
    startup_thread.finished.connect(startup_worker.deleteLater)
    startup_thread.finished.connect(startup_thread.deleteLater)
    startup_thread.started.connect(startup_worker.run)

    try:
        try:
            aplicar_tema(app)
        except OSError:
            app.setStyleSheet(build_stylesheet())
        controlador.iniciar()
        QTimer.singleShot(0, startup_thread.start)
        return app.exec()
    except Exception as exc:  # noqa: BLE001
        _manejar_fallo_arranque(
            exc=exc,
            trace_info=None,
            i18n=i18n,
            splash=splash,
            startup_thread=startup_thread,
            app=app,
            watchdog_timer=None,
        )
        return 2
