from __future__ import annotations

import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path


def configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8")],
        force=True,
    )


def write_crash_log(exc_type, exc, tb, log_dir: Path) -> Path:
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


def install_exception_hook(log_dir: Path) -> None:
    def _handler(exc_type, exc, tb) -> None:
        try:
            write_crash_log(exc_type, exc, tb, log_dir)
        except OSError:
            pass
        logging.critical("Unhandled exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _handler
