from __future__ import annotations

from contextlib import AbstractContextManager
from contextvars import ContextVar, Token
from datetime import datetime, timezone
import uuid
from typing import Any

_CORRELATION_ID: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_RESULT_ID: ContextVar[str | None] = ContextVar("result_id", default=None)


def generate_correlation_id() -> str:
    return str(uuid.uuid4())


def get_correlation_id() -> str | None:
    return _CORRELATION_ID.get()


def get_result_id() -> str | None:
    return _RESULT_ID.get()


def set_correlation_id(correlation_id: str | None) -> Token[str | None]:
    return _CORRELATION_ID.set(correlation_id)


def set_result_id(result_id: str | None) -> Token[str | None]:
    return _RESULT_ID.set(result_id)


def reset_correlation_id(token: Token[str | None]) -> None:
    _CORRELATION_ID.reset(token)


def reset_result_id(token: Token[str | None]) -> None:
    _RESULT_ID.reset(token)


class OperationContext(AbstractContextManager["OperationContext"]):
    def __init__(self, operation_name: str) -> None:
        self.operation_name = operation_name
        self.correlation_id = generate_correlation_id()
        self._correlation_token: Token[str | None] | None = None
        self._result_token: Token[str | None] | None = None

    def __enter__(self) -> "OperationContext":
        self._correlation_token = set_correlation_id(self.correlation_id)
        self._result_token = set_result_id(None)
        return self

    def __exit__(self, exc_type: object, exc: object, exc_tb: object) -> None:
        if self._result_token is not None:
            reset_result_id(self._result_token)
        if self._correlation_token is not None:
            reset_correlation_id(self._correlation_token)
        return None


def log_event(logger: Any, event_name: str, payload: dict[str, Any], correlation_id: str) -> dict[str, Any]:
    result_id = payload.get("result_id")
    if isinstance(result_id, str):
        set_result_id(result_id)

    event = {
        "event": event_name,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    logger.info(
        event_name,
        extra={
            "correlation_id": correlation_id,
            "result_id": result_id,
            "extra": event,
        },
    )
    return event
