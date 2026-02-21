from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from app.core.observability import get_correlation_id, get_result_id

DEFAULT_LOG_MAX_BYTES = 1_048_576
DEFAULT_LOG_BACKUP_COUNT = 10
MAIN_LOG_NAME = "seguimiento.log"
ERROR_OPERATIVO_LOG_NAME = "error_operativo.log"
CRASH_LOG_NAME = "crash.log"
LEGACY_MAIN_LOG_NAME = "app.log"
LEGACY_CRASH_LOG_NAME = "crashes.log"


class JsonLinesFormatter(logging.Formatter):
    """Emite eventos JSONL para facilitar ingesta y búsqueda en tooling externo."""

    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "modulo": record.module,
            "funcion": record.funcName,
            "mensaje": record.getMessage(),
            "correlation_id": self._resolve_correlation_id(record),
        }

        result_id = getattr(record, "result_id", None) or get_result_id()
        if result_id:
            event["result_id"] = result_id

        payload_extra = getattr(record, "extra", None)
        if isinstance(payload_extra, dict) and payload_extra:
            event["extra"] = payload_extra

        if record.exc_info:
            event["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(event, ensure_ascii=False)

    @staticmethod
    def _resolve_correlation_id(record: logging.LogRecord) -> str | None:
        record_value = getattr(record, "correlation_id", None)
        if record_value:
            return str(record_value)
        return get_correlation_id()


class LevelOnlyFilter(logging.Filter):
    def __init__(self, level: int) -> None:
        super().__init__()
        self._level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == self._level


class CrashOnlyFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.CRITICAL


def _build_rotating_handler(
    log_path: Path,
    *,
    max_bytes: int,
    backup_count: int,
    level: int,
    level_only: int | None = None,
    only_crashes: bool = False,
) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(JsonLinesFormatter())
    if level_only is not None:
        handler.addFilter(LevelOnlyFilter(level_only))
    if only_crashes:
        handler.addFilter(CrashOnlyFilter())
    return handler


def _safe_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def configure_logging(
    log_dir: Path,
    *,
    max_bytes: int | None = None,
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
    level: int = logging.INFO,
) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    resolved_max_bytes = max_bytes or _safe_int_env("HORAS_LOG_MAX_BYTES", DEFAULT_LOG_MAX_BYTES)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    main_handler = _build_rotating_handler(
        log_dir / MAIN_LOG_NAME,
        max_bytes=resolved_max_bytes,
        backup_count=backup_count,
        level=level,
    )
    operational_error_handler = _build_rotating_handler(
        log_dir / ERROR_OPERATIVO_LOG_NAME,
        max_bytes=resolved_max_bytes,
        backup_count=backup_count,
        level=logging.ERROR,
        level_only=logging.ERROR,
    )
    crash_handler = _build_rotating_handler(
        log_dir / CRASH_LOG_NAME,
        max_bytes=resolved_max_bytes,
        backup_count=backup_count,
        level=logging.CRITICAL,
        only_crashes=True,
    )

    root_logger.addHandler(main_handler)
    root_logger.addHandler(operational_error_handler)
    root_logger.addHandler(crash_handler)

    # Compatibilidad controlada: conservamos logs legacy para instalaciones/scripts previos.
    root_logger.addHandler(
        _build_rotating_handler(
            log_dir / LEGACY_MAIN_LOG_NAME,
            max_bytes=resolved_max_bytes,
            backup_count=backup_count,
            level=level,
        )
    )
    root_logger.addHandler(
        _build_rotating_handler(
            log_dir / LEGACY_CRASH_LOG_NAME,
            max_bytes=resolved_max_bytes,
            backup_count=backup_count,
            level=logging.CRITICAL,
            only_crashes=True,
        )
    )


def log_operational_error(
    logger: logging.Logger,
    message: str,
    *,
    exc: BaseException | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    exc_info: Any = False
    if exc is not None:
        exc_info = (type(exc), exc, exc.__traceback__)

    payload = {"extra": extra} if extra else None
    logger.error(message, exc_info=exc_info, extra=payload)


def write_crash_log(exc_type: type[BaseException], exc: BaseException, tb: Any, log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("app.crash")
    logger.critical(
        "Unhandled exception",
        exc_info=(exc_type, exc, tb),
        extra={
            "extra": {
                "python": sys.version,
                "executable": sys.executable,
                "cwd": str(Path.cwd()),
            }
        },
    )
    return log_dir / CRASH_LOG_NAME


def install_exception_hook(log_dir: Path) -> None:
    def _handler(exc_type, exc, tb) -> None:
        try:
            write_crash_log(exc_type, exc, tb, log_dir)
        except OSError:
            pass

    sys.excepthook = _handler
