from __future__ import annotations

import pytest

from app.infrastructure.sheets_gateway_puros import (
    ensure_headers,
    ensure_uuid_header,
    find_uuid_row,
    is_non_empty_payload,
    map_gateway_error,
    merge_values_for_upsert,
    normalize_cell,
    normalize_headers,
    normalize_payload,
    normalize_rows,
    parse_a1_range,
)


@pytest.mark.parametrize(
    ("range_name", "expected"),
    [
        ("delegadas!A1", ("delegadas", "A", 1, "A", 1)),
        ("solicitudes!B2:C4", ("solicitudes", "B", 2, "C", 4)),
        ("'Hoja 1'!AA10:AB11", ("Hoja 1", "AA", 10, "AB", 11)),
        ("'O''Brien'!A2", ("O'Brien", "A", 2, "A", 2)),
        ("  cuadrantes!c3:d8  ", ("cuadrantes", "C", 3, "D", 8)),
    ],
)
def test_parse_a1_range_validos(range_name: str, expected: tuple[str, str, int, str, int]) -> None:
    assert parse_a1_range(range_name) == expected


@pytest.mark.parametrize("range_name", ["", "A1", "hoja!A", "hoja!0", "' '!A1", "hoja!A0", "hoja!A1:B0"])
def test_parse_a1_range_invalidos(range_name: str) -> None:
    with pytest.raises(ValueError):
        parse_a1_range(range_name)


@pytest.mark.parametrize(("value", "expected"), [(None, ""), ("  hola ", "hola"), (4, "4")])
def test_normalize_cell(value, expected: str) -> None:
    assert normalize_cell(value) == expected


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ([" id ", "", None], ["id", "col_2", "col_3"]),
        (["uuid", "nombre"], ["uuid", "nombre"]),
    ],
)
def test_normalize_headers(headers, expected) -> None:
    assert normalize_headers(headers) == expected


def test_normalize_payload_completa_faltantes() -> None:
    payload = normalize_payload(["uuid", "nombre", "email"], [" abc ", " Ana "])
    assert payload == {"uuid": "abc", "nombre": "Ana", "email": ""}


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"a": " ", "b": ""}, False),
        ({"a": " x ", "b": ""}, True),
        ({"a": None}, False),
    ],
)
def test_is_non_empty_payload(payload, expected: bool) -> None:
    assert is_non_empty_payload(payload) is expected


def test_normalize_rows_descarta_filas_vacias_y_trim() -> None:
    values = [["uuid", "nombre"], ["  ", ""], [" u-1 ", " Ana "], [None, " Beto "]]
    assert normalize_rows(values) == [(3, {"uuid": "u-1", "nombre": "Ana"}), (4, {"uuid": "", "nombre": "Beto"})]


@pytest.mark.parametrize(
    ("headers", "row", "expected"),
    [
        (["uuid"], {"uuid": "1"}, ["uuid"]),
        ([], {"uuid": "1", "nombre": "Ana"}, ["uuid", "nombre"]),
    ],
)
def test_ensure_headers(headers, row, expected) -> None:
    assert ensure_headers(headers, row) == expected


@pytest.mark.parametrize(
    ("records", "uuid_value", "expected"),
    [
        ([{"uuid": "a"}, {"uuid": " b "}], "b", 3),
        ([{"uuid": "a"}], "", None),
        ([{"uuid": "a"}], "x", None),
    ],
)
def test_find_uuid_row(records, uuid_value: str, expected: int | None) -> None:
    assert find_uuid_row(records, uuid_value) == expected


def test_merge_values_for_upsert_con_fallback() -> None:
    values = merge_values_for_upsert(["uuid", "nombre", "email"], {"uuid": "1", "email": "a@a"}, {"nombre": "Ana"})
    assert values == ["1", "Ana", "a@a"]


@pytest.mark.parametrize(
    ("headers", "expected_headers", "created"),
    [(["uuid", "nombre"], ["uuid", "nombre"], False), (["nombre"], ["nombre", "uuid"], True)],
)
def test_ensure_uuid_header(headers, expected_headers, created: bool) -> None:
    assert ensure_uuid_header(headers) == (expected_headers, created)


class _ExcConStatus(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class _Response:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _ExcConResponse(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.response = _Response(status_code)


@pytest.mark.parametrize(
    ("exc", "expected_message"),
    [
        (_ExcConStatus(404, "not found"), "No se encontró el spreadsheet o la worksheet solicitada."),
        (_ExcConStatus(403, "forbidden"), "Permisos insuficientes para acceder a Google Sheets."),
        (_ExcConStatus(429, "rate limited"), "Google Sheets devolvió rate limit o error temporal."),
        (_ExcConResponse(500, "boom"), "Google Sheets devolvió rate limit o error temporal."),
        (RuntimeError("permission denied"), "Permisos insuficientes para acceder a Google Sheets."),
        (RuntimeError("otra cosa"), "Error de sincronización con Google Sheets: otra cosa"),
    ],
)
def test_map_gateway_error(exc: Exception, expected_message: str) -> None:
    mapped = map_gateway_error(exc)
    assert isinstance(mapped, RuntimeError)
    assert str(mapped) == expected_message
