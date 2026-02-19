from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import datetime, timezone
import uuid
from typing import Any


def generate_correlation_id() -> str:
    return str(uuid.uuid4())


class OperationContext(AbstractContextManager["OperationContext"]):
    def __init__(self, operation_name: str) -> None:
        self.operation_name = operation_name
        self.correlation_id = generate_correlation_id()

    def __enter__(self) -> "OperationContext":
        return self

    def __exit__(self, exc_type: object, exc: object, exc_tb: object) -> None:
        return None


def log_event(logger: Any, event_name: str, payload: dict[str, Any], correlation_id: str) -> dict[str, Any]:
    event = {
        "event": event_name,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    logger.info(event)
    return event
