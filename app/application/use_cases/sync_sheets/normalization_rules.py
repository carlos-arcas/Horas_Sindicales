from __future__ import annotations

from typing import Any

from app.application.use_cases import sync_sheets_core


# Se extrae esta normalización para poder probar reglas de parsing sin dependencia de IO.
def normalize_remote_solicitud_row(row: dict[str, Any], worksheet_name: str) -> dict[str, Any]:
    return sync_sheets_core.normalize_remote_solicitud_row(row, worksheet_name)


def normalize_remote_uuid(value: Any) -> str:
    return str(value or "").strip()
