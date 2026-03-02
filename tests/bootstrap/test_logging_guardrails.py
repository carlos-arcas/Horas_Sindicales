from __future__ import annotations

from app.bootstrap import logging as logging_bootstrap


def test_redact_event_payload_redacta_recursivo() -> None:
    evento = {
        "mensaje": "token=abcd1234",
        "extra": {
            "nivel_1": {
                "secreto": "token=topsecret",
                "lista": ["api_key=ZZZ", {"nested": "authorization=bearer abc"}],
            }
        },
    }

    redacted = logging_bootstrap._redact_event_payload(evento)

    assert "topsecret" not in str(redacted)
    assert "abcd1234" not in str(redacted)
    assert "bearer abc" not in str(redacted).lower()


def test_flush_logging_handlers_no_falla_si_handler_explota() -> None:
    class HandlerRoto:
        def flush(self) -> None:
            raise RuntimeError("boom")

    class HandlerOk:
        def __init__(self) -> None:
            self.flushed = False

        def flush(self) -> None:
            self.flushed = True

    ok = HandlerOk()
    root_logger = logging_bootstrap.logging.getLogger()
    originales = list(root_logger.handlers)
    root_logger.handlers = [HandlerRoto(), ok]

    try:
        logging_bootstrap.flush_logging_handlers()
    finally:
        root_logger.handlers = originales

    assert ok.flushed is True
