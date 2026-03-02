from __future__ import annotations

import logging


logger = logging.getLogger(__name__)

try:
    from presentacion.i18n import CATALOGO, I18nManager
except ImportError:  # pragma: no cover - fallback for headless/unit-test environments
    CATALOGO = {}
    I18nManager = None
    logger.warning(
        "I18N_FALLBACK_ACTIVE_SYNC_PERMISSION_MESSAGE",
        extra={"event": "I18N_FALLBACK_ACTIVE_SYNC_PERMISSION_MESSAGE"},
    )


def build_sync_permission_blocked_message(*, service_account_email: str | None) -> str:
    """Construye mensaje de permisos usando i18n o fallback estático para pruebas sin UI."""

    lang_catalog = CATALOGO.get("es", {})
    account_email = (service_account_email or "<email no disponible>").strip() or "<email no disponible>"
    return lang_catalog.get(
        "sync_permission_blocked_message_with_email",
        "Permisos insuficientes en Google Sheets. Comparte la hoja con la cuenta de servicio: {service_account_email}",
    ).format(service_account_email=account_email)
