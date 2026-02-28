from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from typing import Any


_KEY_VALUE_PATTERNS = [
    re.compile(
        r'(?i)("?(?:access_token|refresh_token|id_token|token|client_secret|api_key|private_key|client_email)"?\s*[:=]\s*)("[^"]*"|\'[^\']*\'|[^,\s}\]]+)'  # noqa: E501
    ),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)([^\s,;]+)"),
]
_CREDENTIALS_PATH_PATTERN = re.compile(
    r"(?i)(?:[a-z]:\\[^\s'\"]*credentials\.json|/[^\s'\"]*credentials\.json)"
)
_CREDENTIALS_FILENAME_PATTERN = re.compile(r"(?i)credentials\.json")


def redactar_texto(texto: str) -> str:
    redacted = texto
    for pattern in _KEY_VALUE_PATTERNS:
        redacted = pattern.sub(r"\1<REDACTED>", redacted)
    redacted = _CREDENTIALS_PATH_PATTERN.sub("<CRED_PATH>", redacted)
    redacted = _CREDENTIALS_FILENAME_PATTERN.sub("<REDACTED>", redacted)
    return redacted


def _redactar_valor(value: Any) -> Any:
    if isinstance(value, str):
        return redactar_texto(value)
    if isinstance(value, Mapping):
        return {key: _redactar_valor(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_redactar_valor(item) for item in value]
    return value


class LoggingSecretsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redactar_texto(record.msg)

        if isinstance(record.args, Mapping):
            record.args = {key: _redactar_valor(value) for key, value in record.args.items()}
        elif isinstance(record.args, tuple):
            record.args = tuple(_redactar_valor(value) for value in record.args)
        elif isinstance(record.args, list):
            record.args = [_redactar_valor(value) for value in record.args]

        for key, value in list(record.__dict__.items()):
            if key in {"msg", "args", "exc_info", "exc_text", "stack_info"}:
                continue
            if isinstance(value, (str, Mapping, Sequence)) and not isinstance(value, (bytes, bytearray)):
                record.__dict__[key] = _redactar_valor(value)

        extra_payload = getattr(record, "extra", None)
        if isinstance(extra_payload, Mapping):
            record.extra = {key: _redactar_valor(value) for key, value in extra_payload.items()}

        return True
