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
    from app.ui.theme import build_stylesheet

    from PySide6.QtWidgets import QApplication, QMessageBox

    from presentacion.i18n import I18nManager
    from presentacion.orquestador_arranque import OrquestadorArranqueUI
    from presentacion.splash_window import SplashWindow

    app = QApplication([])
    i18n = I18nManager("es")
    splash = SplashWindow(i18n)
    splash.show()
    app.processEvents()

    try:
        try:
            aplicar_tema(app)
        except OSError:
            app.setStyleSheet(build_stylesheet())

        if container is None:
            from app.bootstrap.container import build_container

            resolved_container = build_container()
        else:
            resolved_container = container
        deps_arranque = _construir_dependencias_arranque(resolved_container)
        i18n.set_idioma(deps_arranque.obtener_idioma_ui.ejecutar())
        orquestador = OrquestadorArranqueUI(deps_arranque, i18n)

        if not orquestador.resolver_onboarding():
            splash.close()
            return 0

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
        _instalar_menu_ayuda(window, i18n, ReiniciarOnboarding(resolved_container.repositorio_preferencias))
        if orquestador.debe_iniciar_maximizada():
            window.showMaximized()
        else:
            window.show()
        splash.close()
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
