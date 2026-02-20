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
        except OSError:
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
    from PySide6.QtWidgets import QApplication

    from app.application.base_cuadrantes_service import BaseCuadrantesService
    from app.application.conflicts_service import ConflictsService
    from app.application.sheets_service import SheetsService
    from app.application.sync_sheets_use_case import SyncSheetsUseCase
    from app.application.use_cases.alert_engine import AlertEngine
    from app.application.use_cases.health_check import HealthCheckUseCase
    from app.application.use_cases import GrupoConfigUseCases, PersonaUseCases, SolicitudUseCases
    from app.infrastructure.db import get_connection
    from app.infrastructure.local_config_store import LocalConfigStore
    from app.infrastructure.health_probes import DefaultConnectivityProbe, SheetsConfigProbe, SQLiteLocalDbProbe
    from app.infrastructure.repos_conflicts_sqlite import SQLiteConflictsRepository
    from app.infrastructure.migrations import run_migrations
    from app.infrastructure.repos_sqlite import (
        CuadranteRepositorySQLite,
        GrupoConfigRepositorySQLite,
        PersonaRepositorySQLite,
        SolicitudRepositorySQLite,
    )
    from app.infrastructure.sheets_client import SheetsClient
    from app.infrastructure.sheets_gateway_gspread import SheetsGatewayGspread
    from app.infrastructure.sheets_repository import SheetsRepository
    from app.infrastructure.sync_sheets_adapter import SyncSheetsAdapter
    from app.infrastructure.seed import seed_if_empty
    from app.ui.main_window import MainWindow

    connection = get_connection()
    run_migrations(connection)
    seed_if_empty(connection)

    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    grupo_repo = GrupoConfigRepositorySQLite(connection)
    cuadrante_repo = CuadranteRepositorySQLite(connection)

    base_cuadrantes_service = BaseCuadrantesService(persona_repo, cuadrante_repo)
    base_cuadrantes_service.ensure_for_all_personas()
    persona_use_cases = PersonaUseCases(persona_repo, base_cuadrantes_service)
    solicitud_use_cases = SolicitudUseCases(solicitud_repo, persona_repo, grupo_repo)
    grupo_use_cases = GrupoConfigUseCases(grupo_repo)
    config_store = LocalConfigStore()
    sheets_client = SheetsClient()
    sheets_repository = SheetsRepository()
    sheets_gateway = SheetsGatewayGspread(sheets_client, sheets_repository)
    sheets_service = SheetsService(config_store, sheets_gateway)
    sync_port = SyncSheetsAdapter(get_connection, config_store, sheets_client, sheets_repository)
    sync_service = SyncSheetsUseCase(sync_port)
    health_check_use_case = HealthCheckUseCase(
        SheetsConfigProbe(config_store, sheets_client),
        DefaultConnectivityProbe(),
        SQLiteLocalDbProbe(get_connection),
    )
    alert_engine = AlertEngine()
    conflicts_repository = SQLiteConflictsRepository(connection)
    conflicts_service = ConflictsService(
        conflicts_repository,
        lambda: config_store.load().device_id if config_store.load() else "",
    )

    app = QApplication([])
    window = MainWindow(
        persona_use_cases,
        solicitud_use_cases,
        grupo_use_cases,
        sheets_service,
        sync_service,
        conflicts_service,
        health_check_use_case,
        alert_engine,
    )
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

    return _run_app()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("Error no controlado en entrypoint")
        exc_type, _, tb = sys.exc_info()
        log_dir = LOG_DIR or _resolve_log_dir()
        if exc_type and tb:
            _write_crash_log(exc_type, exc, tb, log_dir)
        print("Se produjo un error interno. Revisa el archivo de logs para más detalles.")
        raise
