from __future__ import annotations

from app.domain.sheets_errors import SheetsPermissionError


def test_sheets_permission_error_serializes_safe_context_without_secrets() -> None:
    error = SheetsPermissionError(
        "Permiso denegado",
        service_account_email="svc-account@demo.iam.gserviceaccount.com",
        spreadsheet_id="sheet-abc",
        worksheet="solicitudes",
    )

    payload = error.to_safe_payload()
    rendered = str(error)
    represented = repr(error)

    assert payload["service_account_email"] == "svc-account@demo.iam.gserviceaccount.com"
    assert payload["spreadsheet_id"] == "sheet-abc"
    assert payload["worksheet"] == "solicitudes"
    assert "private_key" not in rendered
    assert "private_key" not in represented
    assert "service_account_email=svc-account@demo.iam.gserviceaccount.com" in rendered
