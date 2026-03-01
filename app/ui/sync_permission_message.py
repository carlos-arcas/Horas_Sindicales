from __future__ import annotations

from presentacion.i18n import CATALOGO


def build_sync_permission_blocked_message(*, service_account_email: str | None) -> str:
    lang_catalog = CATALOGO.get("es", {})
    account_email = (service_account_email or "").strip()
    if account_email:
        return lang_catalog.get(
            "sync_permission_blocked_message_with_email",
            "La sincronización está bloqueada por permisos.\nComparte el spreadsheet con {service_account_email} como Editor.",
        ).format(service_account_email=account_email)
    return lang_catalog.get(
        "sync_permission_blocked_message_without_email",
        "La sincronización está bloqueada por permisos.\nComparte el spreadsheet con la cuenta de servicio como Editor.",
    )
