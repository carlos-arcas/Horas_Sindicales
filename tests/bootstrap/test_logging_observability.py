from __future__ import annotations

import json
import logging

from app.bootstrap import logging as bootstrap_logging


class _FlushOkHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.flushed = 0

    def emit(self, record: logging.LogRecord) -> None:
        return None

    def flush(self) -> None:
        self.flushed += 1


class _FlushFailHandler(_FlushOkHandler):
    def flush(self) -> None:
        self.flushed += 1
        raise RuntimeError("boom flush")


def test_redact_event_payload_es_recursivo_en_dicts_listas_y_tuplas() -> None:
    event = {
        "mensaje": 'token="abc123"',
        "extra": {
            "nivel_1": {
                "authorization": "access_token=secreto",
                "items": [
                    "client_secret=ultra-secreto",
                    {"ruta": "/tmp/credentials.json"},
                    ("refresh_token=xyz", 7),
                ],
            },
            "bandera": True,
            "conteo": 3,
        },
    }

    redacted = bootstrap_logging._redact_event_payload(event)

    assert redacted["mensaje"] == "token=<REDACTED>"
    assert redacted["extra"]["nivel_1"]["authorization"] == "access_token=<REDACTED>"
    assert redacted["extra"]["nivel_1"]["items"][0] == "client_secret=<REDACTED>"
    assert redacted["extra"]["nivel_1"]["items"][1]["ruta"] == "<CRED_PATH>"
    assert redacted["extra"]["nivel_1"]["items"][2] == ("refresh_token=<REDACTED>", 7)
    assert redacted["extra"]["bandera"] is True
    assert redacted["extra"]["conteo"] == 3


def test_flush_logging_handlers_es_tolerante_a_fallos() -> None:
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    ok_handler = _FlushOkHandler()
    fail_handler = _FlushFailHandler()
    root_logger.handlers = [ok_handler, fail_handler]

    try:
        bootstrap_logging.flush_logging_handlers()
    finally:
        root_logger.handlers = original_handlers

    assert ok_handler.flushed == 1
    assert fail_handler.flushed == 1


def test_json_formatter_conserva_estructura_jsonl_y_redacta_extra_anidado() -> None:
    formatter = bootstrap_logging.JsonLinesFormatter()
    record = logging.LogRecord(
        name="tests.logging",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="evento token=abc123",
        args=(),
        exc_info=None,
    )
    record.extra = {
        "payload": {
            "credenciales": ["client_secret=valor", {"ruta": "/tmp/credentials.json"}],
            "ok": True,
        }
    }

    event = json.loads(formatter.format(record))

    assert event["mensaje"] == "evento token=<REDACTED>"
    assert event["extra"]["payload"]["credenciales"][0] == "client_secret=<REDACTED>"
    assert event["extra"]["payload"]["credenciales"][1]["ruta"] == "<CRED_PATH>"
    assert event["extra"]["payload"]["ok"] is True
    assert event["level"] == "INFO"
