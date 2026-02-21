from __future__ import annotations

import json
import logging
import traceback
import uuid
from pathlib import Path
from types import TracebackType

from app.bootstrap.logging import CRASH_LOG_NAME
from app.bootstrap.settings import resolve_log_dir
from app.core.observability import generate_correlation_id, get_correlation_id, set_correlation_id


def generar_id_incidente() -> str:
    return f"INC-{uuid.uuid4().hex[:12].upper()}"


def _asegurar_correlation_id() -> str:
    correlation_id = get_correlation_id()
    if correlation_id:
        return correlation_id
    correlation_id = generate_correlation_id()
    set_correlation_id(correlation_id)
    return correlation_id


def _escribir_fallback_crash_log(
    *,
    incident_id: str,
    correlation_id: str,
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType,
) -> None:
    log_dir = resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    crash_file = log_dir / CRASH_LOG_NAME
    payload = {
        "incident_id": incident_id,
        "correlation_id": correlation_id,
        "error_type": exc_type.__name__,
        "error_message": str(exc_value),
        "stacktrace": "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
    }
    with crash_file.open("a", encoding="utf-8") as handler:
        handler.write(json.dumps(payload, ensure_ascii=False) + "\n")


def manejar_excepcion_global(
    exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType
) -> str:
    incident_id = generar_id_incidente()
    correlation_id = _asegurar_correlation_id()
    logger = logging.getLogger("app.global_exception")

    try:
        logger.exception(
            "Excepción no controlada. incident_id=%s",
            incident_id,
            exc_info=(exc_type, exc_value, exc_traceback),
            extra={"incident_id": incident_id, "correlation_id": correlation_id},
        )
    except Exception:  # noqa: BLE001
        _escribir_fallback_crash_log(
            incident_id=incident_id,
            correlation_id=correlation_id,
            exc_type=exc_type,
            exc_value=exc_value,
            exc_traceback=exc_traceback,
        )

    return incident_id

