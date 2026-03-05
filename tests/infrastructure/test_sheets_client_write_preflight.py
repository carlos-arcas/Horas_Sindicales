from __future__ import annotations

import gspread
import pytest

from app.domain.sheets_errors import SheetsConfigError, SheetsPermissionError
from app.infrastructure.sheets_client import SheetsClient


class _Cell:
    def __init__(self, value: str) -> None:
        self.value = value


class _WorksheetFake:
    def __init__(self, *, valor_inicial: str = "", falla_en: str | None = None, error: Exception | None = None) -> None:
        self.valor_actual = valor_inicial
        self.falla_en = falla_en
        self.error = error
        self.batch_update_calls: list[dict[str, object]] = []
        self.update_calls: list[tuple[str, list[list[str]], str]] = []

    def acell(self, celda: str) -> _Cell:
        assert celda == "ZZ1"
        return _Cell(self.valor_actual)

    def update(self, celda: str, valores: list[list[str]], *, value_input_option: str) -> None:
        if self.falla_en == "update" and self.error is not None:
            raise self.error
        if self.falla_en == "restore" and len(self.update_calls) >= 1 and self.error is not None:
            raise self.error
        self.update_calls.append((celda, valores, value_input_option))
        self.valor_actual = valores[0][0]

    def batch_update(self, body: dict[str, object]) -> None:
        self.batch_update_calls.append(body)


class _SpreadsheetFake:
    def __init__(self, worksheet: _WorksheetFake) -> None:
        self.id = "sheet-123"
        self._worksheet = worksheet
        self.batch_update_calls: list[dict[str, object]] = []

    def worksheet(self, _nombre: str) -> _WorksheetFake:
        return self._worksheet

    def batch_update(self, body: dict[str, object]) -> None:
        self.batch_update_calls.append(body)


class _ForbiddenResp:
    status_code = 403
    text = '{"error": {"code": 403, "message": "The caller does not have permission", "status": "PERMISSION_DENIED"}}'


class _BadRequestResp:
    status_code = 400
    text = '{"error": {"code": 400, "message": "Invalid argument", "status": "INVALID_ARGUMENT"}}'


def _build_client(worksheet: _WorksheetFake) -> tuple[SheetsClient, _SpreadsheetFake]:
    client = SheetsClient()
    spreadsheet = _SpreadsheetFake(worksheet)
    client._spreadsheet = spreadsheet
    return client, spreadsheet


def test_check_write_access_no_usa_batch_update_vacio() -> None:
    worksheet = _WorksheetFake(valor_inicial="anterior")
    client, spreadsheet = _build_client(worksheet)

    client.check_write_access("solicitudes")

    assert spreadsheet.batch_update_calls == []
    assert worksheet.batch_update_calls == []


def test_check_write_access_hace_escritura_reversible() -> None:
    worksheet = _WorksheetFake(valor_inicial="valor-original")
    client, _ = _build_client(worksheet)

    client.check_write_access("solicitudes")

    assert len(worksheet.update_calls) == 2
    assert worksheet.update_calls[1][1] == [["valor-original"]]


@pytest.mark.parametrize(
    ("respuesta", "error_esperado"),
    [
        (_ForbiddenResp(), SheetsPermissionError),
        (_BadRequestResp(), SheetsConfigError),
    ],
)
def test_check_write_access_mapea_errores_api(respuesta, error_esperado) -> None:
    worksheet = _WorksheetFake(falla_en="update", error=gspread.exceptions.APIError(respuesta))
    client, _ = _build_client(worksheet)

    with pytest.raises(error_esperado):
        client.check_write_access("solicitudes")
