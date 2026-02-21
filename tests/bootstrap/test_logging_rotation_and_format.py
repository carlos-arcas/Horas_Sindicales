from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler

from app.bootstrap.logging import (
    CRASH_LOG_NAME,
    ERROR_OPERATIVO_LOG_NAME,
    LevelOnlyFilter,
    configure_logging,
)

MIN_FIELDS = {"timestamp", "level", "modulo", "funcion", "mensaje", "correlation_id"}


def test_logging_writes_jsonl_with_minimum_fields(tmp_path) -> None:
    configure_logging(tmp_path, max_bytes=4096, backup_count=2)

    logger = logging.getLogger("tests.rotation")
    logger.info("primer evento")
    logger.info("segundo evento", extra={"correlation_id": "cid-001", "result_id": "res-001", "extra": {"k": "v"}})

    lines = (tmp_path / "seguimiento.log").read_text(encoding="utf-8").splitlines()
    assert lines
    for line in lines:
        event = json.loads(line)
        assert MIN_FIELDS.issubset(event.keys())

    latest = json.loads(lines[-1])
    assert latest["correlation_id"] == "cid-001"
    assert latest["result_id"] == "res-001"
    assert latest["extra"]["k"] == "v"


def test_logging_rotation_creates_backup_files(tmp_path) -> None:
    configure_logging(tmp_path, max_bytes=200, backup_count=3)
    logger = logging.getLogger("tests.rotation")

    for index in range(40):
        logger.info("evento-%s %s", index, "x" * 120)

    rotated_files = sorted(tmp_path.glob("seguimiento.log.*"))
    assert rotated_files


def test_operational_error_handler_exists_with_error_level(tmp_path) -> None:
    configure_logging(tmp_path, max_bytes=4096, backup_count=2)

    handlers = [h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)]
    operational_handler = next(h for h in handlers if h.baseFilename.endswith(ERROR_OPERATIVO_LOG_NAME))

    assert operational_handler.level == logging.ERROR
    assert any(isinstance(filter_, LevelOnlyFilter) for filter_ in operational_handler.filters)


def test_error_log_writes_only_error_events(tmp_path) -> None:
    configure_logging(tmp_path, max_bytes=4096, backup_count=2)
    logger = logging.getLogger("tests.error_operativo")

    try:
        raise RuntimeError("database is locked")
    except RuntimeError as exc:
        logger.error("Error operativo sincronizando", exc_info=exc)

    error_lines = (tmp_path / ERROR_OPERATIVO_LOG_NAME).read_text(encoding="utf-8").splitlines()
    assert error_lines
    event = json.loads(error_lines[-1])
    assert event["level"] == "ERROR"
    assert "RuntimeError: database is locked" in event["exc_info"]


def test_critical_goes_to_crash_log_and_not_to_operational_error(tmp_path) -> None:
    configure_logging(tmp_path, max_bytes=4096, backup_count=2)
    logger = logging.getLogger("tests.crash")

    try:
        raise ValueError("fallo crítico")
    except ValueError:
        logger.critical("error crítico no controlado", exc_info=True)

    crash_lines = (tmp_path / CRASH_LOG_NAME).read_text(encoding="utf-8").splitlines()
    assert crash_lines
    crash_event = json.loads(crash_lines[-1])
    assert crash_event["level"] == "CRITICAL"
    assert "ValueError: fallo crítico" in crash_event["exc_info"]

    operational_lines = (tmp_path / ERROR_OPERATIVO_LOG_NAME).read_text(encoding="utf-8").splitlines()
    assert not operational_lines
