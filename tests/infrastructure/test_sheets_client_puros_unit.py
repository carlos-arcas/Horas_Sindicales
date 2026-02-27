from __future__ import annotations

import pytest

from app.infrastructure.sheets_client_puros import (
    normalize_batch_get_result,
    worksheet_from_operation_name,
    worksheet_name_from_range,
)
from app.infrastructure.sheets_errors import SheetsApiCompatibilityError


def test_normalize_batch_get_result_desde_dict_y_lista() -> None:
    from_dict = normalize_batch_get_result(
        ["A!A1:B2", "B!A1:A2"],
        {
            "valueRanges": [
                {"range": "A!A1:B2", "values": [["1", "2"]]},
                {"range": "B!A1:A2", "values": [["x"]]},
            ]
        },
    )
    assert from_dict == {"A!A1:B2": [["1", "2"]], "B!A1:A2": [["x"]]}

    from_list = normalize_batch_get_result(["A", "B", "C"], [[["1"]], "x", [["3"]]])
    assert from_list == {"A": [["1"]], "B": [], "C": [["3"]]}


def test_normalize_batch_get_result_filtra_entradas_invalidas() -> None:
    result = normalize_batch_get_result(
        ["A"],
        {"valueRanges": [None, {"range": 123, "values": [["x"]]}, {"range": "A", "values": "bad"}]},
    )
    assert result == {"A": []}


@pytest.mark.parametrize(
    ("range_name", "expected"),
    [
        ("solicitudes!A1:B2", "solicitudes"),
        ("'Hoja 1'!A1", "Hoja 1"),
        ("'O''Brien'!A1", "O'Brien"),
        ("solo_nombre", "solo_nombre"),
        ("   ", None),
    ],
)
def test_worksheet_name_from_range(range_name: str, expected: str | None) -> None:
    assert worksheet_name_from_range(range_name) == expected


@pytest.mark.parametrize(
    ("operation_name", "expected"),
    [
        ("worksheet.append_rows(solicitudes)", "solicitudes"),
        ("spreadsheet.values_batch_get(12 ranges)", "12 ranges"),
        ("sin_parentesis", None),
        ("call()", None),
    ],
)
def test_worksheet_from_operation_name(operation_name: str, expected: str | None) -> None:
    assert worksheet_from_operation_name(operation_name) == expected


def test_normalize_batch_get_result_lanza_compatibilidad_para_tipos_no_soportados() -> None:
    with pytest.raises(SheetsApiCompatibilityError):
        normalize_batch_get_result(["A"], object())
