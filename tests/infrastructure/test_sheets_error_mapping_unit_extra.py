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
from app.infrastructure.sheets_errors import map_gspread_exception


class _Resp:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def _api_error(status_code: int, text: str) -> gspread.exceptions.APIError:
    return gspread.exceptions.APIError(_Resp(status_code, text))


def test_map_gspread_exception_mapea_rate_limit_variantes() -> None:
    for status, text in [
        (429, "RESOURCE_EXHAUSTED"),
        (503, "temporary unavailable"),
        (400, "quota exceeded"),
    ]:
        mapped = map_gspread_exception(_api_error(status, text))
        assert isinstance(mapped, SheetsRateLimitError)


def test_map_gspread_exception_mapea_api_disabled_notfound_y_permission() -> None:
    assert isinstance(
        map_gspread_exception(_api_error(400, "Google Sheets API has not been used in project")),
        SheetsApiDisabledError,
    )
    assert isinstance(
        map_gspread_exception(_api_error(404, "Requested entity was not found")),
        SheetsNotFoundError,
    )
    assert isinstance(
        map_gspread_exception(_api_error(403, "PERMISSION_DENIED")),
        SheetsPermissionError,
    )


def test_map_gspread_exception_mapea_credenciales_y_fallbacks() -> None:
    not_found = FileNotFoundError("missing")
    not_found.filename = "/tmp/cred.json"

    mapped_not_found = map_gspread_exception(not_found)
    mapped_json = map_gspread_exception(json.JSONDecodeError("bad", "{}", 0))
    mapped_default = map_gspread_exception(DefaultCredentialsError("bad creds"))
    mapped_attr = map_gspread_exception(AttributeError("sin atributo"))
    mapped_other = map_gspread_exception(RuntimeError("fallo inesperado"))

    assert isinstance(mapped_not_found, SheetsCredentialsError)
    assert "/tmp/cred.json" in str(mapped_not_found)
    assert isinstance(mapped_json, SheetsCredentialsError)
    assert isinstance(mapped_default, SheetsCredentialsError)
    assert str(mapped_attr) == "sin atributo"
    assert isinstance(mapped_other, SheetsConfigError)
