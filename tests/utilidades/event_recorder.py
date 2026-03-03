from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_DATETIME_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b")
_HEX_ID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27}\b")
_LONG_INT_RE = re.compile(r"\b\d{8,}\b")


class EventRecorder:
    """Captura eventos de interacción de UI para snapshots golden deterministas."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def record(self, tipo: str, data: dict[str, Any]) -> None:
        self._events.append({"tipo": tipo, "data": _normalize_value(data)})

    def snapshot(self) -> list[dict[str, Any]]:
        return deepcopy(self._events)

    def to_json(self) -> str:
        return json.dumps(self.snapshot(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def normalize_dynamic_value(value: Any) -> Any:
    return _normalize_value(value)


def _normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize_value(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        return [_normalize_value(v) for v in value]
    if isinstance(value, tuple):
        return [_normalize_value(v) for v in value]
    if isinstance(value, Path):
        return "<RUTA>"
    if isinstance(value, str):
        return _normalize_text(value)
    return value


def _normalize_text(text: str) -> str:
    normalized = _DATETIME_RE.sub("<FECHA>", text)
    normalized = _DATE_RE.sub("<FECHA>", normalized)
    normalized = _HEX_ID_RE.sub("<ID>", normalized)
    normalized = _LONG_INT_RE.sub("<ID>", normalized)
    if "/" in normalized or "\\" in normalized:
        path_like = normalized.startswith("/") or re.match(r"^[A-Za-z]:\\", normalized)
        if path_like:
            return "<RUTA>"
    return normalized
