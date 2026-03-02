from __future__ import annotations

from presentacion.i18n import CATALOGO


def construir_mensaje_permiso_sheets(*, service_account_email: str | None) -> tuple[str, dict[str, str]]:
    account_email = (service_account_email or "").strip()
    if account_email:
        return "sync_permission_blocked_message_with_email", {"service_account_email": account_email}
    return "sync_permission_blocked_message_without_email", {}


def build_sync_permission_blocked_message(*, service_account_email: str | None) -> str:
    lang_catalog = CATALOGO.get("es", {})
    key, params = construir_mensaje_permiso_sheets(service_account_email=service_account_email)
    fallback = {
        "sync_permission_blocked_message_with_email": "La sincronización está bloqueada por permisos.\nComparte el spreadsheet con {service_account_email} como Editor.",
        "sync_permission_blocked_message_without_email": "La sincronización está bloqueada por permisos.\nComparte el spreadsheet con la cuenta de servicio como Editor.",
    }
    return lang_catalog.get(key, fallback[key]).format(**params)
