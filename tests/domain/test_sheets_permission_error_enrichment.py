from __future__ import annotations

from app.domain.sheets_errors import SheetsPermissionError


def test_sheets_permission_error_preserva_contexto_enriquecido() -> None:
    error = SheetsPermissionError(
        "Permiso denegado",
        spreadsheet_id="sheet-123",
        worksheet="solicitudes",
    ).enriquecer_email_cuenta_servicio("sync-bot@example.iam.gserviceaccount.com")

    assert error.spreadsheet_id == "sheet-123"
    assert error.worksheet == "solicitudes"
    assert error.service_account_email == "sync-bot@example.iam.gserviceaccount.com"


def test_sheets_permission_error_safe_payload_no_expone_secretos() -> None:
    error = SheetsPermissionError(
        "Permiso denegado",
        spreadsheet_id="sheet-123",
        worksheet="solicitudes",
        service_account_email="sync-bot@example.iam.gserviceaccount.com",
    )

    payload = error.to_safe_payload()

    assert payload == {
        "spreadsheet_id": "…et-123",
        "worksheet": "solicitudes",
        "service_account_email": "sync-bot@example.iam.gserviceaccount.com",
    }
    assert "private_key" not in str(error)


def test_sheets_permission_error_muestra_spreadsheet_completo_si_politica_lo_permite(
    monkeypatch,
) -> None:
    monkeypatch.setenv("HORAS_PERMITIR_SPREADSHEET_ID_COMPLETO", "true")
    error = SheetsPermissionError("Permiso denegado", spreadsheet_id="sheet-123")

    payload = error.to_safe_payload()

    assert payload["spreadsheet_id"] == "sheet-123"
