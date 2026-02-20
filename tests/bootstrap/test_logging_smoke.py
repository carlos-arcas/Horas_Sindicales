from __future__ import annotations

import logging
import sys

from app.bootstrap.logging import configure_logging, install_exception_hook


def test_configure_logging_writes_log_file(tmp_path) -> None:
    configure_logging(tmp_path)

    logger = logging.getLogger("tests.logging_smoke")
    logger.info("smoke log message")

    log_file = tmp_path / "app.log"
    assert log_file.exists()
    assert "smoke log message" in log_file.read_text(encoding="utf-8")


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

        crash_log = tmp_path / "crash.log"
        assert crash_log.exists()
        assert "RuntimeError: boom" in crash_log.read_text(encoding="utf-8")
    finally:
        sys.excepthook = original_hook
