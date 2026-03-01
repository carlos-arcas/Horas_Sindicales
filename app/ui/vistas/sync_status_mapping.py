from __future__ import annotations

from app.ui.copy_catalog import copy_text


_SYNC_STATUS_COPY_KEYS: dict[str, str] = {
    "IDLE": "ui.sync.estado_en_espera",
    "RUNNING": "ui.sync.estado_pendiente_sincronizando",
    "CONFIG_INCOMPLETE": "ui.sync.estado_error_config_incompleta",
}


def status_to_label(status: str) -> str:
    copy_key = _SYNC_STATUS_COPY_KEYS.get(status)
    if copy_key is None:
        return status
    return copy_text(copy_key)
