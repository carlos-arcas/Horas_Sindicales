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


class SheetsClientError(Exception):
    pass


class SheetsApiCompatibilityError(SheetsClientError):
    pass


def extract_response_status_code(ex: Exception) -> int | None:
    response = getattr(ex, "response", None)
    return getattr(response, "status_code", None)


def _extract_api_error_text(ex: gspread.exceptions.APIError) -> str:
    response = getattr(ex, "response", None)
    if response is not None:
        text = getattr(response, "text", "")
        if text:
            return text
    return str(ex)


def normalize_error_text(text: str) -> str:
    return text.strip().lower()


def _credentials_not_found_message(path: Optional[str]) -> str:
    if path:
        return f"No se encuentra credentials.json en {path}."
    return "No se encuentra credentials.json."


def _is_rate_limited_api_error(text_lower: str, status_code: int | None) -> bool:
    if status_code in {429, 500, 503}:
        return True
    return any(
        token in text_lower
        for token in (
            "[429]",
            "resource_exhausted",
            "rate_limit_exceeded",
            "quota exceeded",
            "read requests per minute per user",
        )
    )


def classify_api_error(text_lower: str, status_code: int | None) -> Exception:
    if _is_rate_limited_api_error(text_lower, status_code):
        return SheetsRateLimitError("Límite de Google Sheets alcanzado. Espera 1 minuto y reintenta.")
    if "google sheets api has not been used" in text_lower or "it is disabled" in text_lower:
        return SheetsApiDisabledError("La API de Google Sheets no está habilitada en tu proyecto de Google Cloud.")
    if "[404]" in text_lower or "requested entity was not found" in text_lower:
        return SheetsNotFoundError("El Spreadsheet ID/URL no es válido o la hoja no existe.")
    if status_code == 403 or "[403]" in text_lower or "permission_denied" in text_lower:
        return SheetsPermissionError("La hoja no está compartida con la cuenta de servicio.")
    return SheetsConfigError(text_lower)


def map_gspread_exception(ex: Exception) -> Exception:
    if isinstance(ex, SheetsRateLimitError | SheetsClientError):
        return ex
    if isinstance(ex, gspread.exceptions.APIError):
        text = _extract_api_error_text(ex)
        text_lower = normalize_error_text(text)
        status_code = extract_response_status_code(ex)
        return classify_api_error(text_lower, status_code)
    if isinstance(ex, FileNotFoundError):
        path = getattr(ex, "filename", None)
        return SheetsCredentialsError(_credentials_not_found_message(path))
    if isinstance(ex, json.JSONDecodeError | DefaultCredentialsError):
        return SheetsCredentialsError("El credentials.json no es válido. Revisa el contenido del archivo.")
    if isinstance(ex, AttributeError):
        return SheetsClientError(str(ex))
    return SheetsConfigError(str(ex))
