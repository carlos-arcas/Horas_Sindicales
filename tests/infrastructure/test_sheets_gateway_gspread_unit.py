from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.infrastructure.sheets_gateway_gspread import SheetsGatewayGspread


@dataclass
class _Config:
    credentials_path: str
    spreadsheet_id: str


class _WorksheetFake:
    def __init__(self, values: list[list[str]], records: list[dict[str, str]] | None = None) -> None:
        self._values = values
        self._records = records or []
        self.updated: list[tuple[str, list[list[str]]]] = []
        self.updated_cell: tuple[int, int, str] | None = None
        self.appended: list[list[str]] = []

    def get_all_values(self):
        return self._values

    def row_values(self, _):
        return self._values[0] if self._values else []

    def get_all_records(self):
        return self._records

    def update(self, ref: str, payload: list[list[str]]):
        self.updated.append((ref, payload))

    def update_cell(self, row: int, col: int, value: str):
        self.updated_cell = (row, col, value)

    def append_row(self, row: list[str], value_input_option: str):
        assert value_input_option == "USER_ENTERED"
        self.appended.append(row)


class _SpreadsheetFake:
    def __init__(self, worksheet: _WorksheetFake) -> None:
        self.title = "Libro"
        self.id = "abc"
        self._worksheet = worksheet

    def worksheet(self, _name: str):
        return self._worksheet


class _ClientFake:
    def __init__(self, spreadsheet) -> None:
        self._spreadsheet = spreadsheet

    def open_spreadsheet(self, *_args):
        return self._spreadsheet


class _RepoFake:
    def ensure_schema(self, *_args):
        return ["ok"]


def test_read_rows_filtra_vacias(tmp_path) -> None:
    ws = _WorksheetFake([["uuid", "nombre"], ["", ""], ["1", " Ana "]])
    gateway = SheetsGatewayGspread(_ClientFake(_SpreadsheetFake(ws)), _RepoFake())

    rows = gateway.read_personas(_Config(str(tmp_path / "creds.json"), "sheet"))

    assert rows == [(3, {"uuid": "1", "nombre": "Ana"})]


def test_upsert_actualiza_por_uuid(tmp_path) -> None:
    ws = _WorksheetFake([["uuid", "nombre"]], records=[{"uuid": "u1", "nombre": "Viejo"}])
    gateway = SheetsGatewayGspread(_ClientFake(_SpreadsheetFake(ws)), _RepoFake())

    gateway.upsert_persona(_Config(str(tmp_path / "creds.json"), "sheet"), {"uuid": "u1", "nombre": "Nuevo"})

    assert ws.updated == [("A2", [["u1", "Nuevo"]])]


def test_backfill_uuid_agrega_columna_si_no_existe(tmp_path) -> None:
    ws = _WorksheetFake([["nombre"]])
    gateway = SheetsGatewayGspread(_ClientFake(_SpreadsheetFake(ws)), _RepoFake())

    gateway.backfill_uuid(_Config(str(tmp_path / "creds.json"), "sheet"), "delegadas", 7, "u-9")

    assert ws.updated[0] == ("A1", [["nombre", "uuid"]])
    assert ws.updated_cell == (7, 2, "u-9")


def test_gateway_mapea_errores(tmp_path) -> None:
    class _BrokenClient:
        def open_spreadsheet(self, *_args):
            raise RuntimeError("permission denied")

    gateway = SheetsGatewayGspread(_BrokenClient(), _RepoFake())
    with pytest.raises(RuntimeError, match="Permisos insuficientes"):
        gateway.read_personas(_Config(str(tmp_path / "creds.json"), "sheet"))
