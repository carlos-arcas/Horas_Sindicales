from __future__ import annotations

import logging
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
from app.ui.qt_safe import is_qt_valid, safe_call

LOGGER = logging.getLogger(__name__)


def _es_objeto_qt_valido(objeto) -> bool:
    return is_qt_valid(objeto)


def _cerrar_splash_seguro(splash) -> None:
    if splash is None:
        return
    if not _es_objeto_qt_valido(splash):
        return
    try:
        if hasattr(splash, "request_close"):
            splash.request_close()
            return
        if hasattr(splash, "hide"):
            splash.hide()
        if hasattr(splash, "close"):
            splash.close()
    except RuntimeError:
        return


def _stop_watchdog_en_main_thread(watchdog_timer) -> None:
    if watchdog_timer is None or not hasattr(watchdog_timer, "stop"):
        return
    if not _es_objeto_qt_valido(watchdog_timer):
        return
    try:
        from PySide6.QtCore import QTimer
    except Exception:
        try:
            watchdog_timer.stop()
        except RuntimeError:
            return
        return
    try:
        QTimer.singleShot(0, watchdog_timer.stop)
    except RuntimeError:
        return


class _CoordinadorArranqueConCierreDeterminista:
    def _detener_watchdog_idempotente(self) -> None:
        if not _es_objeto_qt_valido(self.watchdog_timer):
            return
        try:
            _stop_watchdog_en_main_thread(self.watchdog_timer)
        except RuntimeError:
            return

    def _cerrar_splash_idempotente(self) -> None:
        if self._splash_cerrado:
            return
        self._splash_cerrado = True
        if not _es_objeto_qt_valido(self.splash):
            return
        _cerrar_splash_seguro(self.splash)

    def on_finished(self, startup_payload) -> None:
        self.terminado = True
        try:
            self._detener_watchdog_idempotente()
            self._cerrar_splash_idempotente()
            self._solicitar_cierre_thread()
            if isinstance(startup_payload, tuple) and len(startup_payload) == 3:
                resolved_container, deps_arranque, idioma = startup_payload
                self.i18n.set_idioma(idioma)
            else:
                resultado_arranque = startup_payload
                self.i18n.set_idioma(resultado_arranque.idioma_inicial)
                resolved_container = self.container_seed or _construir_container_ui()
                deps_arranque = _construir_dependencias_arranque(resolved_container)
            orquestador = self.orquestador_factory(deps_arranque, self.i18n)
            self._cerrar_splash_idempotente()
            if not orquestador.resolver_onboarding():
                self.app.exit(0)
                return
            self._cerrar_splash_idempotente()
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
            import sys

            self._reportar_fallo_arranque(
                exc=exc,
                trace_info=sys.exc_info(),
                i18n=self.i18n,
                splash=self.splash,
                startup_thread=self.thread,
                app=self.app,
                watchdog_timer=self.watchdog_timer,
            )





def _traducir_arranque(key: str, **kwargs: object) -> str:
    from presentacion.i18n import CATALOGO

    base = CATALOGO["es"].get(key, key)
    return base.format(**kwargs) if kwargs else base


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
    from PySide6.QtCore import QThread, QTimer, Qt
    from PySide6.QtWidgets import QApplication

    if getattr(app, "_fallo_arranque_en_progreso", False):
        return str(getattr(app, "_fallo_arranque_incident_id", "") or incident_id or "")

    app._fallo_arranque_en_progreso = True
    app._fallo_arranque_correlation_id = str(uuid.uuid4())
    resolved_incident_id = incident_id or _resolver_incident_id(exc, trace_info)
    app._fallo_arranque_incident_id = resolved_incident_id

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
        extra={
            "incident_id": resolved_incident_id,
            "correlation_id": app._fallo_arranque_correlation_id,
        },
    )

    def _safe_quit_thread() -> None:
        if not _es_objeto_qt_valido(startup_thread):
            return
        try:
            safe_call(startup_thread, "quit")
        except RuntimeError:
            return

    def _mostrar_dialogo_error() -> None:
        if getattr(app, "_fallo_arranque_dialogo_mostrado", False):
            return
        app._fallo_arranque_dialogo_mostrado = True

        if dialogo_factory is None:
            from app.ui.dialogos.dialogo_error_arranque import DialogoErrorArranque

            resolved_dialogo_factory = DialogoErrorArranque
        else:
            resolved_dialogo_factory = dialogo_factory

        dialogo = resolved_dialogo_factory(
            i18n,
            titulo=i18n.t("splash_error_titulo"),
            mensaje_usuario=mensaje_usuario or i18n.t("startup_error_dialog_message"),
            incident_id=resolved_incident_id,
            detalles=resolved_detalles,
            parent=None,
        )

        def _exit_con_codigo() -> None:
            QTimer.singleShot(0, lambda: QApplication.exit(2))

        safe_call(dialogo, "setWindowModality", Qt.ApplicationModal)
        safe_call(dialogo, "setWindowFlag", Qt.WindowStaysOnTopHint, True)
        if hasattr(dialogo, "finished"):
            dialogo.finished.connect(_exit_con_codigo)
        safe_call(dialogo, "show")
        safe_call(dialogo, "raise_")
        safe_call(dialogo, "activateWindow")
        if not hasattr(dialogo, "finished") and hasattr(dialogo, "exec"):
            safe_call(dialogo, "exec")
            _exit_con_codigo()

    def _do_fail_safe() -> None:
        if getattr(app, "_startup_fail_safe_ejecutado", False):
            return
        app._startup_fail_safe_ejecutado = True
        _stop_watchdog_en_main_thread(watchdog_timer)
        _safe_quit_thread()
        _cerrar_splash_seguro(splash)
        if _es_objeto_qt_valido(splash) and hasattr(splash, "deleteLater"):
            try:
                QTimer.singleShot(0, splash.deleteLater)
            except RuntimeError:
                pass
        _mostrar_dialogo_error()

    app_thread = app.thread() if is_qt_valid(app) and hasattr(app, "thread") else None
    if app_thread is not None and QThread.currentThread() is not app_thread:
        QTimer.singleShot(0, app, _do_fail_safe)
    else:
        _do_fail_safe()
    return resolved_incident_id




def _construir_container_ui():
    from app.bootstrap.container import build_container

    return build_container()


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

    from app.entrypoints.coordinador_arranque import CoordinadorArranque
    from PySide6.QtCore import QThread, QTimer, Qt
    from PySide6.QtWidgets import QApplication

    startup_timeout_ms = _resolver_startup_timeout_ms()

    app = QApplication([])
    i18n = I18nManager("es")
    splash = SplashWindow(i18n)
    splash.show()

    startup_thread = QThread(splash)
    startup_worker = TrabajadorArranque(_traducir_arranque)
    startup_worker.moveToThread(startup_thread)
    splash.registrar_arranque(startup_thread, startup_worker)

    watchdog_timer = QTimer(splash)
    watchdog_timer.setSingleShot(True)
    watchdog_timer.setInterval(startup_timeout_ms)

    class CoordinadorArranquePrincipal(_CoordinadorArranqueConCierreDeterminista, CoordinadorArranque):
        pass

    controlador = CoordinadorArranquePrincipal(
        app=app,
        i18n=i18n,
        splash=splash,
        startup_timeout_ms=startup_timeout_ms,
        container_seed=container,
        startup_thread=startup_thread,
        startup_worker=startup_worker,
        watchdog_timer=watchdog_timer,
        main_window_factory=lambda resolved_container, deps_arranque: MainWindow(
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
        ),
        orquestador_factory=OrquestadorArranqueUI,
        instalar_menu_ayuda=_instalar_menu_ayuda,
        fallo_arranque_handler=_manejar_fallo_arranque,
    )

    splash.registrar_watchdog(watchdog_timer)

    watchdog_timer.timeout.connect(controlador.on_timeout, Qt.ConnectionType.QueuedConnection)
    startup_worker.progreso.connect(controlador.on_progreso, Qt.ConnectionType.QueuedConnection)
    startup_worker.finished.connect(controlador.on_finished, Qt.ConnectionType.QueuedConnection)
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
