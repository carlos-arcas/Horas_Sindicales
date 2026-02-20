from __future__ import annotations

import json
import logging

from app.bootstrap.logging import configure_logging


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


def test_crash_log_contains_exception_info(tmp_path) -> None:
    configure_logging(tmp_path, max_bytes=4096, backup_count=2)
    logger = logging.getLogger("tests.crash")

    try:
        raise ValueError("fallo controlado")
    except ValueError:
        logger.exception("error al procesar")

    crash_lines = (tmp_path / "crashes.log").read_text(encoding="utf-8").splitlines()
    assert crash_lines
    crash_event = json.loads(crash_lines[-1])
    assert crash_event["level"] == "ERROR"
    assert "ValueError: fallo controlado" in crash_event["exc_info"]
