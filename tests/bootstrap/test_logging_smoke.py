from __future__ import annotations

import json
import logging
import sys

from app.bootstrap.logging import CRASH_LOG_NAME, configure_logging, install_exception_hook


def test_configure_logging_writes_jsonl_log_file(tmp_path) -> None:
    configure_logging(tmp_path)

    logger = logging.getLogger("tests.logging_smoke")
    logger.info("smoke log message")

    log_file = tmp_path / "seguimiento.log"
    assert log_file.exists()
    event = json.loads(log_file.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert event["mensaje"] == "smoke log message"


def test_install_exception_hook_writes_crash_log(tmp_path) -> None:
    original_hook = sys.excepthook
    configure_logging(tmp_path)
    install_exception_hook(tmp_path)

    try:
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            exc_type, exc, tb = sys.exc_info()
            assert exc_type is not None and exc is not None and tb is not None
            sys.excepthook(exc_type, exc, tb)

        crash_log = tmp_path / CRASH_LOG_NAME
        assert crash_log.exists()
        crash_event = json.loads(crash_log.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert crash_event["level"] == "CRITICAL"
        assert "RuntimeError: boom" in crash_event["exc_info"]
    finally:
        sys.excepthook = original_hook
