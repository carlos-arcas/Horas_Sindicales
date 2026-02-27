from __future__ import annotations

import gspread

from app.infrastructure.sheets_repository import SheetsRepository


class _WorksheetFake:
    def __init__(self, *, title: str, existing_headers: list[str] | None = None) -> None:
        self.title = title
        self._existing_headers = existing_headers or []
        self.updated_ranges: list[tuple[str, list[list[str]]]] = []

    def row_values(self, row: int) -> list[str]:
        assert row == 1
        return list(self._existing_headers)

    def update(self, value_range: str, values: list[list[str]]) -> None:
        self.updated_ranges.append((value_range, values))
        self._existing_headers = values[0]


class _SpreadsheetFake:
    def __init__(self, worksheets: dict[str, _WorksheetFake] | None = None) -> None:
        self._worksheets = worksheets or {}

    def worksheet(self, sheet_name: str) -> _WorksheetFake:
        if sheet_name not in self._worksheets:
            raise gspread.WorksheetNotFound(sheet_name)
        return self._worksheets[sheet_name]

    def add_worksheet(self, *, title: str, rows: int, cols: int) -> _WorksheetFake:
        ws = _WorksheetFake(title=title)
        ws.created_rows = rows
        ws.created_cols = cols
        self._worksheets[title] = ws
        return ws


def test_ensure_schema_crea_hoja_y_cabecera_si_no_existe() -> None:
    repository = SheetsRepository()
    spreadsheet = _SpreadsheetFake()

    actions = repository.ensure_schema(spreadsheet, {"solicitudes": ["uuid", "fecha"]})

    ws = spreadsheet.worksheet("solicitudes")
    assert ws.updated_ranges == [("1:1", [["uuid", "fecha"]])]
    assert "Creada hoja 'solicitudes'." in actions
    assert "Cabecera creada en 'solicitudes'." in actions


def test_ensure_schema_agrega_columnas_faltantes_en_hoja_existente() -> None:
    repository = SheetsRepository()
    existing_ws = _WorksheetFake(title="delegadas", existing_headers=["uuid", "nombre"])
    spreadsheet = _SpreadsheetFake({"delegadas": existing_ws})

    actions = repository.ensure_schema(spreadsheet, {"delegadas": ["uuid", "nombre", "email"]})

    assert existing_ws.updated_ranges == [("1:1", [["uuid", "nombre", "email"]])]
    assert actions == ["Cabecera actualizada en 'delegadas' (añadidas 1 columnas)."]
