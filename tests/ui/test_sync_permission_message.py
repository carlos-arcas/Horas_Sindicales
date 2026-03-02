from __future__ import annotations

from app.domain.sheets_errors import SheetsPermissionError
from app.ui.sync_permission_message import build_sync_permission_blocked_message


def test_build_sync_permission_message_with_email() -> None:
    message = build_sync_permission_blocked_message(service_account_email="sync-bot@example.iam.gserviceaccount.com")

    assert "sync-bot@example.iam.gserviceaccount.com" in message
    assert "Editor" in message


def test_build_sync_permission_message_without_email() -> None:
    message = build_sync_permission_blocked_message(service_account_email=None)

    assert "<email no disponible>" in message
    assert "Permisos insuficientes en Google Sheets" in message


def test_sheets_permission_error_can_carry_service_account_email() -> None:
    error = SheetsPermissionError("Sin permisos").enriquecer_email_cuenta_servicio("sync-bot@example.iam.gserviceaccount.com")

    assert error.service_account_email == "sync-bot@example.iam.gserviceaccount.com"
