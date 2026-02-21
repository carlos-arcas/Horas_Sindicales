from __future__ import annotations

import logging
from typing import Any

from app.core.observability import get_correlation_id

operational_logger = logging.getLogger("app.operational_error")


def log_operational_error(
    message: str,
    *,
    exc: BaseException,
    extra: dict[str, Any] | None = None,
) -> None:
    metadata = dict(extra or {})
    correlation_id = metadata.get("correlation_id") or get_correlation_id()
    if correlation_id:
        metadata["correlation_id"] = correlation_id
    operational_logger.error(
        message,
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={"correlation_id": correlation_id, "extra": metadata},
    )
