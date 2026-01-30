from __future__ import annotations

import logging
import traceback
from datetime import datetime
from pathlib import Path

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
    solicitud_use_cases = SolicitudUseCases(solicitud_repo, persona_repo)

    app = QApplication([])
    window = MainWindow(persona_use_cases, solicitud_use_cases)
    window.show()
    app.exec()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_path = Path(__file__).resolve().parent / "crash.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_details = traceback.format_exc()
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}]\n{error_details}\n")
        traceback.print_exc()
        raise
