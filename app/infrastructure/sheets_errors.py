from __future__ import annotations

import json
from typing import Optional

import gspread
from google.auth.exceptions import DefaultCredentialsError

from app.domain.sheets_errors import (
    SheetsApiDisabledError,
    SheetsConfigError,
    SheetsCredentialsError,
    SheetsNotFoundError,
    SheetsPermissionError,
    SheetsRateLimitError,
)


def _extract_api_error_text(ex: gspread.exceptions.APIError) -> str:
    response = getattr(ex, "response", None)
    if response is not None:
        text = getattr(response, "text", "")
        if text:
            return text
    return str(ex)


def _credentials_not_found_message(path: Optional[str]) -> str:
    if path:
        return f"No se encuentra credentials.json en {path}."
    return "No se encuentra credentials.json."


def is_rate_limited_api_error(ex: Exception) -> bool:
    if not isinstance(ex, gspread.exceptions.APIError):
        return False
    text = _extract_api_error_text(ex)
    text_lower = text.lower()
    response = getattr(ex, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code == 429 or "[429]" in text_lower:
        return True
    markers = ("resource_exhausted", "rate_limit_exceeded", "quota exceeded", "too many requests")
    return any(marker in text_lower for marker in markers)


def map_gspread_exception(ex: Exception) -> Exception:
    if isinstance(ex, gspread.exceptions.APIError):
        if is_rate_limited_api_error(ex):
            return SheetsRateLimitError(
                "Límite de Google Sheets alcanzado. Espera 1 minuto y reintenta."
            )
        text = _extract_api_error_text(ex)
        text_lower = text.lower()
        if "google sheets api has not been used" in text_lower or "it is disabled" in text_lower:
            return SheetsApiDisabledError(
                "La API de Google Sheets no está habilitada en tu proyecto de Google Cloud."
            )
        if "[404]" in text_lower or "requested entity was not found" in text_lower:
            return SheetsNotFoundError("El Spreadsheet ID/URL no es válido o la hoja no existe.")
        if "[403]" in text_lower:
            return SheetsPermissionError("La hoja no está compartida con la cuenta de servicio.")
        return SheetsConfigError(text)
    if isinstance(ex, FileNotFoundError):
        path = getattr(ex, "filename", None)
        return SheetsCredentialsError(_credentials_not_found_message(path))
    if isinstance(ex, json.JSONDecodeError):
        return SheetsCredentialsError("El credentials.json no es válido. Revisa el contenido del archivo.")
    if isinstance(ex, DefaultCredentialsError):
        return SheetsCredentialsError("El credentials.json no es válido. Revisa el contenido del archivo.")
    return SheetsConfigError(str(ex))
