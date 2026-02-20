from __future__ import annotations

import argparse
import faulthandler
import logging
import sys
from pathlib import Path

from app.bootstrap.logging import configure_logging, install_exception_hook
from app.bootstrap.settings import project_root, resolve_log_dir
from app.entrypoints.ui_main import run_ui


def _run_selfcheck(log_dir: Path) -> int:
    logger = logging.getLogger(__name__)
    errors = 0
    root = project_root()

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Horas Sindicales")
    parser.add_argument("--selfcheck", action="store_true", help="Valida recursos sin abrir UI")
    args = parser.parse_args(argv)

    log_dir = resolve_log_dir()
    configure_logging(log_dir)
    install_exception_hook(log_dir)
    faulthandler.enable()

    logger = logging.getLogger(__name__)
    logger.info("Log dir: %s", log_dir)
    logger.info("Python: %s", sys.version)
    logger.info("Executable: %s", sys.executable)
    logger.info("CWD: %s", Path.cwd())

    if args.selfcheck:
        return _run_selfcheck(log_dir)
    return run_ui()
