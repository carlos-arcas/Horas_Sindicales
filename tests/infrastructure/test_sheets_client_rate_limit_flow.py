from __future__ import annotations

from types import SimpleNamespace

import gspread
import pytest

from app.domain.sheets_errors import SheetsPermissionError, SheetsRateLimitError
from app.infrastructure.sheets_client import SheetsClient


class _Resp429:
    status_code = 429
    text = "RESOURCE_EXHAUSTED"


class _Resp403:
    status_code = 403
    text = '{"error": {"code": 403, "message": "The caller does not have permission", "status": "PERMISSION_DENIED"}}'


def test_with_rate_limit_retry_reintenta_hasta_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = SheetsClient()
    intentos = {"n": 0}
    sleeps: list[float] = []

    def _operacion() -> str:
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise gspread.exceptions.APIError(_Resp429())
        return "ok"

    monkeypatch.setattr("time.sleep", lambda segundos: sleeps.append(segundos))

    assert cliente._with_rate_limit_retry("lectura", _operacion) == "ok"
    assert intentos["n"] == 3
    assert sleeps == [1, 2]


def test_with_rate_limit_retry_falla_al_agotar_reintentos(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = SheetsClient()
    intentos = {"n": 0}

    def _operacion() -> None:
        intentos["n"] += 1
        raise gspread.exceptions.APIError(_Resp429())

    monkeypatch.setattr("time.sleep", lambda _segundos: None)

    with pytest.raises(SheetsRateLimitError, match="Límite de Google Sheets"):
        cliente._with_rate_limit_retry("lectura", _operacion)

    assert intentos["n"] == 5


def test_with_rate_limit_retry_error_permisos_mapea_y_registra(monkeypatch: pytest.MonkeyPatch) -> None:
    cliente = SheetsClient()
    cliente._spreadsheet = SimpleNamespace(id="spreadsheet-x")
    capturado: dict[str, str | None] = {}

    def _operacion() -> None:
        raise gspread.exceptions.APIError(_Resp403())

    def _fake_log(error: SheetsPermissionError, *, spreadsheet_id: str | None = None, worksheet_name: str | None = None) -> None:
        capturado["mensaje"] = str(error)
        capturado["spreadsheet_id"] = spreadsheet_id
        capturado["worksheet_name"] = worksheet_name

    monkeypatch.setattr(cliente, "_log_permission_error", _fake_log)

    with pytest.raises(SheetsPermissionError):
        cliente._with_rate_limit_retry("worksheet.get_all_values(Resumen)", _operacion)

    assert capturado["spreadsheet_id"] == "spreadsheet-x"
    assert capturado["worksheet_name"] == "Resumen"
