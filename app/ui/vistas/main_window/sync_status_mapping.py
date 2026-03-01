from __future__ import annotations

from app.ui.copy_catalog import copy_text

try:
    from app.ui.patterns import STATUS_PATTERNS
except Exception:  # pragma: no cover
    STATUS_PATTERNS = {}


_STATUS_TO_PATTERN = {
    "OK": "CONFIRMED",
    "OK_WARN": "WARNING",
    "ERROR": "ERROR",
}


def _pattern_badge(status: str) -> str | None:
    pattern_name = _STATUS_TO_PATTERN.get(status)
    if pattern_name is None:
        return None
    pattern = STATUS_PATTERNS.get(pattern_name)
    as_badge = getattr(pattern, "as_badge", None)
    if callable(as_badge):
        return as_badge()
    return None


def status_to_label(status: str) -> str:
    labels = {
        "IDLE": copy_text("ui.sync.estado_en_espera"),
        "RUNNING": copy_text("ui.sync.estado_pendiente_sincronizando"),
        "CONFIG_INCOMPLETE": copy_text("ui.sync.estado_error_config_incompleta"),
    }
    if status in labels:
        return labels[status]
    badge = _pattern_badge(status)
    if badge:
        return badge
    return status
