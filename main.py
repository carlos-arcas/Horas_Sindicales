from __future__ import annotations

import argparse
import faulthandler
import logging
import os
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

LOG_DIR: Path | None = None


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _resolve_log_dir() -> Path:
    candidates: list[Path] = []
    env_dir = os.environ.get("HORAS_LOG_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    candidates.append(_project_root() / "logs")
    candidates.append(Path(tempfile.gettempdir()) / "HorasSindicales" / "logs")

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test_file = candidate / "_write_test.tmp"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return candidate
        except OSError:
            continue

    fallback = _project_root()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8")],
        force=True,
    )


def _write_crash_log(exc_type, exc, tb, log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    crash_path = log_dir / "crash.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_details = "".join(traceback.format_exception(exc_type, exc, tb))
    payload = (
        f"[{timestamp}]\n"
        f"Python: {sys.version}\n"
        f"Executable: {sys.executable}\n"
        f"CWD: {Path.cwd()}\n"
        f"Traceback:\n{error_details}\n"
    )
    with crash_path.open("a", encoding="utf-8") as log_file:
        log_file.write(payload)
    return crash_path


def _install_exception_hook(log_dir: Path) -> None:
    def _handler(exc_type, exc, tb) -> None:
        try:
            _write_crash_log(exc_type, exc, tb, log_dir)
        except Exception:
            pass
        logging.critical("Unhandled exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _handler


def _run_selfcheck(log_dir: Path) -> int:
    logger = logging.getLogger(__name__)
    errors = 0
    root = _project_root()

    qss_path = root / "app" / "ui" / "styles" / "cgt_dark.qss"
    if not qss_path.exists():
        logger.error("Falta el archivo QSS: %s", qss_path)
        errors += 1
    else:
        try:
            _ = qss_path.read_text(encoding="utf-8")
            logger.info("QSS cargado correctamente: %s", qss_path)
        except OSError as exc:
            logger.exception("No se pudo leer el QSS: %s", exc)
            errors += 1

    logo_candidates = [root / "logo.png", root / "assets" / "logo.png"]
    if not any(candidate.exists() for candidate in logo_candidates):
        logger.error("No se encontro logo.png en rutas esperadas: %s", logo_candidates)
        errors += 1
    else:
        existing = [candidate for candidate in logo_candidates if candidate.exists()]
        logger.info("Logo encontrado en: %s", existing)

    if errors:
        crash_path = log_dir / "crash.log"
        logger.error("Selfcheck fallo con %s error(es). Verifica recursos. crash.log=%s", errors, crash_path)
        return 1
    logger.info("Selfcheck OK.")
    return 0


def _run_app() -> int:
    logger = logging.getLogger(__name__)

    from PySide6.QtWidgets import QApplication

    from app.application.use_cases import PersonaUseCases, SolicitudUseCases
    from app.infrastructure.db import get_connection
    from app.infrastructure.migrations import run_migrations
    from app.infrastructure.repos_sqlite import PersonaRepositorySQLite, SolicitudRepositorySQLite
    from app.infrastructure.seed import seed_if_empty
    from app.ui.main_window import MainWindow

    connection = get_connection()
    run_migrations(connection)
    seed_if_empty(connection)

    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)

    persona_use_cases = PersonaUseCases(persona_repo)
    solicitud_use_cases = SolicitudUseCases(solicitud_repo, persona_repo)

    app = QApplication([])
    try:
        window = MainWindow(persona_use_cases, solicitud_use_cases)
    except Exception:
        logger.exception("Error construyendo MainWindow")
        raise
    window.show()
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    global LOG_DIR
    parser = argparse.ArgumentParser(description="Horas Sindicales")
    parser.add_argument("--selfcheck", action="store_true", help="Valida recursos sin abrir UI")
    args = parser.parse_args(argv)

    LOG_DIR = _resolve_log_dir()
    _configure_logging(LOG_DIR)
    _install_exception_hook(LOG_DIR)
    faulthandler.enable()

    logger = logging.getLogger(__name__)
    logger.info("Log dir: %s", LOG_DIR)
    logger.info("Python: %s", sys.version)
    logger.info("Executable: %s", sys.executable)
    logger.info("CWD: %s", Path.cwd())

    if args.selfcheck:
        return _run_selfcheck(LOG_DIR)

    try:
        return _run_app()
    except Exception:
        logger.exception("Error en ejecución de la app")
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        exc_type, exc, tb = sys.exc_info()
        log_dir = LOG_DIR or _resolve_log_dir()
        if exc_type and exc and tb:
            _write_crash_log(exc_type, exc, tb, log_dir)
        raise
