from __future__ import annotations

from app.domain.sheets_errors import SheetsPermissionError
from app.ui.vistas.main_window_helpers import show_sync_error_dialog_from_exception


def test_permission_error_shows_only_config_copy_and_guide_actions() -> None:
    captured: dict[str, object] = {}

    show_sync_error_dialog_from_exception(
        error=SheetsPermissionError("Sin permisos", service_account_email="sync-bot@example.iam.gserviceaccount.com"),
        details=None,
        service_account_email="sync-bot@example.iam.gserviceaccount.com",
        show_message_with_details=lambda title, message, _details, _icon, action_buttons=(): captured.update(
            {"title": title, "message": message, "action_buttons": action_buttons}
        ),
        open_options_callback=lambda: None,
        retry_callback=lambda: None,
        open_google_sheets_config_callback=lambda: None,
        open_sync_guide_callback=lambda: None,
        toast_warning=lambda _message, _title, _duration: None,
        clipboard_setter=lambda _value: None,
    )

    labels = [label for label, _ in captured["action_buttons"]]
    assert captured["title"] == "Error de sincronización"
    assert "La hoja no está compartida con la cuenta de servicio" in captured["message"]
    assert labels == [
        "Abrir configuración de Google Sheets",
        "Copiar email de servicio",
        "Abrir guía de sincronización",
    ]
    assert "Reintentar" not in labels


def test_permission_error_hides_copy_action_without_email() -> None:
    captured: dict[str, object] = {}

    show_sync_error_dialog_from_exception(
        error=SheetsPermissionError("Sin permisos"),
        details=None,
        service_account_email=None,
        show_message_with_details=lambda _title, _message, _details, _icon, action_buttons=(): captured.update(
            {"action_buttons": action_buttons}
        ),
        open_options_callback=lambda: None,
        retry_callback=lambda: None,
        open_google_sheets_config_callback=lambda: None,
        open_sync_guide_callback=None,
        toast_warning=lambda _message, _title, _duration: None,
        clipboard_setter=lambda _value: None,
    )

    labels = [label for label, _ in captured["action_buttons"]]
    assert labels == ["Abrir configuración de Google Sheets"]
