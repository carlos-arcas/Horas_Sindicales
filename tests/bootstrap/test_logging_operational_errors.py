from __future__ import annotations

import json
import logging

from app.bootstrap.logging import OPERATIONAL_ERROR_LOG_NAME, configure_logging


def test_operational_error_handler_exists_with_error_level(tmp_path) -> None:
    configure_logging(tmp_path, max_bytes=4096, backup_count=2)

    root_logger = logging.getLogger()
    handler = next((h for h in root_logger.handlers if getattr(h, "baseFilename", "").endswith(OPERATIONAL_ERROR_LOG_NAME)), None)

    assert handler is not None
    assert handler.level == logging.ERROR


def test_error_logs_are_written_to_operational_file(tmp_path) -> None:
    configure_logging(tmp_path, max_bytes=4096, backup_count=2)
    logger = logging.getLogger("tests.operational")

    logger.error("database is locked", extra={"extra": {"operation": "sync"}})

    operational_lines = (tmp_path / OPERATIONAL_ERROR_LOG_NAME).read_text(encoding="utf-8").splitlines()
    assert operational_lines
    event = json.loads(operational_lines[-1])
    assert event["level"] == "ERROR"
    assert event["mensaje"] == "database is locked"


def test_critical_logs_only_go_to_crash_log_policy(tmp_path) -> None:
    configure_logging(tmp_path, max_bytes=4096, backup_count=2)
    logger = logging.getLogger("tests.operational")

    logger.critical("unhandled exception")

    crash_lines = (tmp_path / "crash.log").read_text(encoding="utf-8").splitlines()
    assert crash_lines

    operational_path = tmp_path / OPERATIONAL_ERROR_LOG_NAME
    if operational_path.exists():
        operational_lines = operational_path.read_text(encoding="utf-8").splitlines()
        assert all(json.loads(line)["level"] != "CRITICAL" for line in operational_lines)
