from __future__ import annotations

import json

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
from app.infrastructure.sheets_errors import (
    SheetsClientError,
    _credentials_not_found_message,
    _extract_api_error_text,
    _is_rate_limited_api_error,
    map_gspread_exception,
)


class _Resp:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def _api_error(status_code: int, text: str) -> gspread.exceptions.APIError:
    return gspread.exceptions.APIError(_Resp(status_code, text))


def test_extract_api_error_text_prioriza_response_text() -> None:
    error = _api_error(400, "detalle remoto")
    assert _extract_api_error_text(error) == "detalle remoto"


def test_credentials_not_found_message_con_y_sin_path() -> None:
    assert _credentials_not_found_message("/tmp/cred.json") == "No se encuentra credentials.json en /tmp/cred.json."
    assert _credentials_not_found_message(None) == "No se encuentra credentials.json."


def test_is_rate_limited_por_status_y_tokens() -> None:
    assert _is_rate_limited_api_error(_api_error(429, "x"), "x") is True
    assert _is_rate_limited_api_error(_api_error(400, "quota exceeded"), "quota exceeded") is True
    assert _is_rate_limited_api_error(_api_error(400, "otro"), "otro") is False


def test_map_gspread_exception_cubre_taxonomia_api() -> None:
    assert isinstance(map_gspread_exception(_api_error(503, "RESOURCE_EXHAUSTED")), SheetsRateLimitError)
    assert isinstance(map_gspread_exception(_api_error(403, "permission_denied")), SheetsPermissionError)
    assert isinstance(map_gspread_exception(_api_error(404, "requested entity was not found")), SheetsNotFoundError)
    assert isinstance(
        map_gspread_exception(_api_error(400, "Google Sheets API has not been used in project")),
        SheetsApiDisabledError,
    )
    fallback = map_gspread_exception(_api_error(400, "fallo no mapeado"))
    assert isinstance(fallback, SheetsConfigError)
    assert str(fallback) == "fallo no mapeado"


def test_map_gspread_exception_cubre_credenciales_y_genericos() -> None:
    not_found = FileNotFoundError("No existe")
    not_found.filename = "/tmp/credenciales.json"
    assert isinstance(map_gspread_exception(not_found), SheetsCredentialsError)
    assert isinstance(map_gspread_exception(json.JSONDecodeError("msg", "{}", 0)), SheetsCredentialsError)
    assert isinstance(map_gspread_exception(DefaultCredentialsError("bad creds")), SheetsCredentialsError)

    attr = map_gspread_exception(AttributeError("attr missing"))
    assert isinstance(attr, SheetsClientError)
    assert str(attr) == "attr missing"

    runtime = map_gspread_exception(RuntimeError("boom"))
    assert isinstance(runtime, SheetsConfigError)
    assert str(runtime) == "boom"


def test_map_gspread_exception_retorna_errores_ya_mapeados() -> None:
    mapped = SheetsRateLimitError("x")
    assert map_gspread_exception(mapped) is mapped
