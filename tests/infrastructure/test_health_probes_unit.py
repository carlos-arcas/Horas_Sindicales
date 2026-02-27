from __future__ import annotations

from dataclasses import dataclass

from app.application.sheets_service import SHEETS_SCHEMA
from app.infrastructure.health_probes import SheetsConfigProbe


@dataclass
class _Config:
    credentials_path: str
    spreadsheet_id: str


class _ConfigStoreFake:
    def __init__(self, config: _Config | None) -> None:
        self._config = config

    def load(self) -> _Config | None:
        return self._config


class _SheetsClientFake:
    def __init__(self, *, worksheets: dict[str, object], header_row: list[str], fail_open: bool = False) -> None:
        self._worksheets = worksheets
        self._header_row = header_row
        self._fail_open = fail_open
        self.opened_with: tuple[str, str] | None = None

    def open_spreadsheet(self, credentials_path, spreadsheet_id: str) -> None:
        if self._fail_open:
            raise RuntimeError("boom")
        self.opened_with = (str(credentials_path), spreadsheet_id)

    def get_worksheets_by_title(self) -> dict[str, object]:
        return self._worksheets

    def read_all_values(self, worksheet_name: str) -> list[list[str]]:
        assert worksheet_name == "solicitudes"
        return [self._header_row]


def test_sheets_config_probe_happy_path_valida_hojas_y_cabeceras(tmp_path) -> None:
    cred_file = tmp_path / "creds.json"
    cred_file.write_text("{}", encoding="utf-8")
    config = _Config(credentials_path=str(cred_file), spreadsheet_id="spreadsheet-id")
    expected_headers = SHEETS_SCHEMA["solicitudes"]
    client = _SheetsClientFake(
        worksheets={"delegadas": object(), "solicitudes": object(), "cuadrantes": object()},
        header_row=expected_headers,
    )

    result = SheetsConfigProbe(_ConfigStoreFake(config), client).check()

    assert client.opened_with == (str(cred_file), "spreadsheet-id")
    assert result["credentials"][0] is True
    assert result["spreadsheet"][0] is True
    assert result["worksheet"][0] is True
    assert result["headers"][0] is True


def test_sheets_config_probe_si_google_falla_marca_errores(tmp_path) -> None:
    cred_file = tmp_path / "creds.json"
    cred_file.write_text("{}", encoding="utf-8")
    config = _Config(credentials_path=str(cred_file), spreadsheet_id="spreadsheet-id")
    client = _SheetsClientFake(
        worksheets={"delegadas": object(), "solicitudes": object(), "cuadrantes": object()},
        header_row=[],
        fail_open=True,
    )

    result = SheetsConfigProbe(_ConfigStoreFake(config), client).check()

    assert result["worksheet"][0] is False
    assert "No se pudo acceder al Spreadsheet" in result["worksheet"][1]
    assert result["headers"] == (False, "No se pudo validar rango/cabeceras.", "open_sync_settings")
