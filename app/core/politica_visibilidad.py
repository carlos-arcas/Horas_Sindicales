from __future__ import annotations

import os


def permitir_spreadsheet_id_completo() -> bool:
    valor = os.getenv("HORAS_PERMITIR_SPREADSHEET_ID_COMPLETO", "").strip().lower()
    return valor in {"1", "true", "yes", "si"}


def proteger_spreadsheet_id(spreadsheet_id: str | None) -> str | None:
    if not spreadsheet_id:
        return None
    if permitir_spreadsheet_id_completo():
        return spreadsheet_id
    suffix = spreadsheet_id[-6:]
    return f"…{suffix}"
