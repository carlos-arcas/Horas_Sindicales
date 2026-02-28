from __future__ import annotations

import sys
from types import TracebackType

from app.bootstrap.container import AppContainer, build_container
from app.bootstrap.exception_handler import manejar_excepcion_global


def construir_mensaje_error_ui(incident_id: str) -> str:
    return f"Ha ocurrido un error inesperado.\nID de incidente: {incident_id}"


def manejar_excepcion_ui(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType,
) -> str:
    from PySide6.QtWidgets import QApplication, QMessageBox

    incident_id = manejar_excepcion_global(exc_type, exc_value, exc_traceback)
    app = QApplication.instance()
    if app is None:
        return incident_id
    try:
        QMessageBox.critical(None, "Error inesperado", construir_mensaje_error_ui(incident_id))
    except Exception:
        # Respaldo: evitar un segundo crash al intentar pintar un diálogo de error.
        pass
    return incident_id


def run_ui(container: AppContainer | None = None) -> int:
    from PySide6.QtWidgets import QApplication

    from app.ui.estilos.apply_theme import aplicar_tema
    from app.ui.main_window import MainWindow
    from app.ui.theme import build_stylesheet

    resolved_container = container or build_container()
    app = QApplication([])
    try:
        aplicar_tema(app)
    except OSError:
        app.setStyleSheet(build_stylesheet())

    try:
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
        )
        window.show()
        return app.exec()
    except Exception:  # noqa: BLE001
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_type is not None and exc_value is not None and exc_traceback is not None:
            manejar_excepcion_ui(exc_type, exc_value, exc_traceback)
        return 2
