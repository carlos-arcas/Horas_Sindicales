from __future__ import annotations

from app.bootstrap.container import AppContainer, build_container


def run_ui(container: AppContainer | None = None) -> int:
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow

    resolved_container = container or build_container()
    app = QApplication([])
    window = MainWindow(
        resolved_container.persona_use_cases,
        resolved_container.solicitud_use_cases,
        resolved_container.grupo_use_cases,
        resolved_container.sheets_service,
        resolved_container.sync_service,
        resolved_container.conflicts_service,
        resolved_container.health_check_use_case,
        resolved_container.alert_engine,
    )
    window.show()
    return app.exec()
