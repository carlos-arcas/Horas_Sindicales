from __future__ import annotations

import logging
import sys
from types import TracebackType

from aplicacion.casos_de_uso.documentos import ObtenerRutaGuiaSync
from aplicacion.casos_de_uso.idioma import GuardarIdiomaUI, ObtenerIdiomaUI
from aplicacion.casos_de_uso.onboarding import MarcarOnboardingCompletado, ObtenerEstadoOnboarding, ReiniciarOnboarding
from aplicacion.casos_de_uso.preferencia_pantalla_completa import (
    GuardarPreferenciaPantallaCompleta,
    ObtenerPreferenciaPantallaCompleta,
)
from app.bootstrap.exception_handler import manejar_excepcion_global
from app.bootstrap.logging import log_operational_error

LOGGER = logging.getLogger(__name__)


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


def _instalar_menu_ayuda(main_window, i18n, reiniciar_onboarding: ReiniciarOnboarding) -> None:
    from PySide6.QtWidgets import QMessageBox

    menu_ayuda = main_window.menuBar().addMenu(i18n.t("menu_ayuda"))
    accion_reiniciar = menu_ayuda.addAction(i18n.t("menu_reiniciar_asistente"))

    def _reiniciar_asistente() -> None:
        reiniciar_onboarding.ejecutar()
        QMessageBox.information(main_window, i18n.t("menu_ayuda"), i18n.t("menu_reiniciar_ok"))

    accion_reiniciar.triggered.connect(_reiniciar_asistente)


def run_ui(container=None) -> int:
    from app.ui.estilos.apply_theme import aplicar_tema
    from app.ui.main_window import MainWindow
    from app.ui.splash_window import SplashWindow
    from app.ui.theme import build_stylesheet
    from presentacion.i18n import I18nManager
    from presentacion.orquestador_arranque import OrquestadorArranqueUI

    from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
    from PySide6.QtWidgets import QApplication, QMessageBox

    class _StartupWorker(QObject):
        terminado = Signal(object, object, object)

        def __init__(self, container_seed) -> None:
            super().__init__()
            self._container_seed = container_seed

        @Slot()
        def run(self) -> None:
            try:
                resolved_container = self._container_seed
                if resolved_container is None:
                    from app.bootstrap.container import build_container

                    resolved_container = build_container()
                deps_arranque = _construir_dependencias_arranque(resolved_container)
                idioma = deps_arranque.obtener_idioma_ui.ejecutar()
                self.terminado.emit((resolved_container, deps_arranque, idioma), None, None)
            except Exception as exc:  # noqa: BLE001
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.terminado.emit(None, exc, (exc_type, exc_value, exc_traceback))

    app = QApplication([])
    i18n = I18nManager("es")
    splash = SplashWindow(i18n)
    splash.show()

    startup_thread = QThread()
    startup_worker = _StartupWorker(container)
    startup_worker.moveToThread(startup_thread)

    def _finalizar_con_error(exc: Exception | None, trace_info) -> None:
        if trace_info is not None and all(trace_info):
            incident_id = manejar_excepcion_ui(trace_info[0], trace_info[1], trace_info[2])
        else:
            incident_id = "unknown"
        log_operational_error(
            LOGGER,
            i18n.t("splash_error_mensaje", incident_id=incident_id),
            exc=exc,
            extra={"incident_id": incident_id},
        )
        QMessageBox.critical(None, i18n.t("splash_error_titulo"), i18n.t("splash_error_mensaje", incident_id=incident_id))
        splash.close()
        app.exit(2)

    def _abrir_ventana_principal(startup_payload) -> None:
        resolved_container, deps_arranque, idioma = startup_payload
        i18n.set_idioma(idioma)
        orquestador = OrquestadorArranqueUI(deps_arranque, i18n)

        if not orquestador.resolver_onboarding():
            splash.close()
            app.exit(0)
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
        app.setProperty("_main_window_ref", window)
        _instalar_menu_ayuda(window, i18n, ReiniciarOnboarding(resolved_container.repositorio_preferencias))
        if orquestador.debe_iniciar_maximizada():
            window.showMaximized()
        else:
            window.show()
        splash.close()

    @Slot(object, object, object)
    def _on_startup_terminado(startup_payload, exc, trace_info) -> None:
        startup_thread.quit()
        startup_thread.wait()
        startup_worker.deleteLater()
        startup_thread.deleteLater()
        if exc is not None:
            _finalizar_con_error(exc, trace_info)
            return
        _abrir_ventana_principal(startup_payload)

    startup_worker.terminado.connect(_on_startup_terminado)
    startup_thread.started.connect(startup_worker.run)

    try:
        try:
            aplicar_tema(app)
        except OSError:
            app.setStyleSheet(build_stylesheet())
        QTimer.singleShot(0, startup_thread.start)
        return app.exec()
    except Exception as exc:  # noqa: BLE001
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_type is not None and exc_value is not None and exc_traceback is not None:
            incident_id = manejar_excepcion_ui(exc_type, exc_value, exc_traceback)
            log_operational_error(
                LOGGER,
                i18n.t("splash_error_mensaje", incident_id=incident_id),
                exc=exc,
                extra={"incident_id": incident_id},
            )
            QMessageBox.critical(None, i18n.t("splash_error_titulo"), i18n.t("splash_error_mensaje", incident_id=incident_id))
        splash.close()
        return 2
