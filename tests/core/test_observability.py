from __future__ import annotations

import logging

from app.core.observability import OperationContext, generate_correlation_id, log_event


def test_operation_context_generates_uuid4_correlation_id() -> None:
    with OperationContext("unit_test") as operation:
        correlation_id = operation.correlation_id

    assert isinstance(correlation_id, str)
    assert len(correlation_id) == 36
    assert correlation_id.count("-") == 4


def test_log_event_returns_structured_event_dict() -> None:
    logger = logging.getLogger("tests.observability")

    event = log_event(
        logger,
        "sync_started",
        {"operation": "sync"},
        "cid-123",
    )

    assert event["event"] == "sync_started"
    assert event["correlation_id"] == "cid-123"
    assert "timestamp" in event
    assert event["payload"] == {"operation": "sync"}


def test_generate_correlation_id_is_unique() -> None:
    first = generate_correlation_id()
    second = generate_correlation_id()

    assert first != second
