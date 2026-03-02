from __future__ import annotations

from presentacion.i18n import CATALOGO


def build_sync_permission_blocked_message(*, service_account_email: str | None) -> str:
    lang_catalog = CATALOGO.get("es", {})
    account_email = (service_account_email or "<email no disponible>").strip() or "<email no disponible>"
    return lang_catalog.get(
        "sync_permission_blocked_message_with_email",
        "Permisos insuficientes en Google Sheets. Comparte la hoja con la cuenta de servicio: {service_account_email}",
    ).format(service_account_email=account_email)
