from __future__ import annotations

import json

import gspread
import pytest
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
    classify_api_error,
    extract_response_status_code,
    map_gspread_exception,
    normalize_error_text,
)


class _Resp:
    def __init__(self, code: int, text: str) -> None:
        self.status_code = code
        self.text = text


@pytest.mark.parametrize(
    "text,code,tipo",
    [
        ("RESOURCE_EXHAUSTED", 429, SheetsRateLimitError),
        ("Google Sheets API has not been used", 400, SheetsApiDisabledError),
        ("Requested entity was not found", 404, SheetsNotFoundError),
        ("PERMISSION_DENIED", 403, SheetsPermissionError),
    ],
)
def test_classify_api_error(text: str, code: int, tipo: type[Exception]) -> None:
    assert isinstance(classify_api_error(text.lower(), code), tipo)


def test_classify_api_error_default_config() -> None:
    err = classify_api_error("algo raro", 400)
    assert isinstance(err, SheetsConfigError)


def test_normalize_error_text() -> None:
    assert normalize_error_text("  HOLA  ") == "hola"


def test_extract_response_status_code() -> None:
    exc = gspread.exceptions.APIError(_Resp(403, "x"))
    assert extract_response_status_code(exc) == 403


def test_extract_response_status_code_sin_response() -> None:
    assert extract_response_status_code(RuntimeError("x")) is None


def test_map_gspread_exception_api_rate_limit() -> None:
    exc = gspread.exceptions.APIError(_Resp(429, "x"))
    assert isinstance(map_gspread_exception(exc), SheetsRateLimitError)


def test_map_gspread_exception_api_con_texto_response() -> None:
    exc = gspread.exceptions.APIError(_Resp(400, "PERMISSION_DENIED"))
    assert isinstance(map_gspread_exception(exc), SheetsPermissionError)


def test_map_gspread_exception_api_fallback_str() -> None:
    class _RespSinTexto:
        status_code = 404
        text = "Requested entity was not found"

    exc = gspread.exceptions.APIError(_RespSinTexto())
    assert isinstance(map_gspread_exception(exc), SheetsNotFoundError)


def test_map_gspread_exception_filenotfound_con_filename() -> None:
    exc = FileNotFoundError()
    exc.filename = "/tmp/cred.json"
    out = map_gspread_exception(exc)
    assert isinstance(out, SheetsCredentialsError)
    assert "/tmp/cred.json" in str(out)


def test_map_gspread_exception_filenotfound_sin_filename() -> None:
    out = map_gspread_exception(FileNotFoundError())
    assert isinstance(out, SheetsCredentialsError)


def test_map_gspread_exception_json_decode() -> None:
    out = map_gspread_exception(json.JSONDecodeError("x", "x", 0))
    assert isinstance(out, SheetsCredentialsError)


def test_map_gspread_exception_default_credentials() -> None:
    out = map_gspread_exception(DefaultCredentialsError("x"))
    assert isinstance(out, SheetsCredentialsError)


def test_map_gspread_exception_attribute_error() -> None:
    out = map_gspread_exception(AttributeError("faltante"))
    assert isinstance(out, SheetsClientError)


def test_map_gspread_exception_passthrough_rate_limit() -> None:
    exc = SheetsRateLimitError("x")
    assert map_gspread_exception(exc) is exc


def test_map_gspread_exception_passthrough_client_error() -> None:
    exc = SheetsClientError("x")
    assert map_gspread_exception(exc) is exc


def test_map_gspread_exception_default() -> None:
    out = map_gspread_exception(RuntimeError("boom"))
    assert isinstance(out, SheetsConfigError)
