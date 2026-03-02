from __future__ import annotations

from app.domain.sheets_errors import SheetsPermissionError, construir_mensaje_permiso_sheets


def test_construir_mensaje_permiso_sheets_con_metadata() -> None:
    error = SheetsPermissionError(
        "403 Forbidden",
        spreadsheet_id="sheet-123",
        worksheet="solicitudes",
        service_account_email="sync-bot@example.iam.gserviceaccount.com",
    )

    mensaje = construir_mensaje_permiso_sheets(error)

    assert "i18n_key=sync.permission_denied" in mensaje
    assert "spreadsheet_id=sheet-123" in mensaje
    assert "worksheet=solicitudes" in mensaje
    assert "service_account_email=sync-bot@example.iam.gserviceaccount.com" in mensaje


def test_construir_mensaje_permiso_sheets_con_fallbacks() -> None:
    mensaje = construir_mensaje_permiso_sheets(SheetsPermissionError("403"))

    assert "spreadsheet_id=desconocido" in mensaje
    assert "worksheet=desconocida" in mensaje
