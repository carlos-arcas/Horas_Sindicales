from __future__ import annotations

import logging

from PySide6.QtWidgets import QApplication

from app.application.use_cases import PersonaUseCases, SolicitudUseCases
from app.infrastructure.db import get_connection
from app.infrastructure.migrations import run_migrations
from app.infrastructure.repos_sqlite import PersonaRepositorySQLite, SolicitudRepositorySQLite
from app.infrastructure.seed import seed_if_empty
from app.ui.main_window import MainWindow


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def main() -> None:
    connection = get_connection()
    run_migrations(connection)
    seed_if_empty(connection)

    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)

    persona_use_cases = PersonaUseCases(persona_repo)
    SolicitudUseCases(solicitud_repo, persona_repo)

    app = QApplication([])
    window = MainWindow(persona_use_cases)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
