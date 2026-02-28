from __future__ import annotations

from app.ui.copy_catalog import copy_keys, copy_text


REQUIRED_KEYS = (
    "solicitudes.tooltip_delegada",
    "solicitudes.tooltip_fecha",
    "solicitudes.tooltip_desde",
    "solicitudes.tooltip_hasta",
    "solicitudes.help_toggle",
    "sync_credenciales.title",
    "sync_credenciales.test_connection",
)


def test_copy_catalog_keys_are_unique() -> None:
    keys = copy_keys()
    assert len(keys) == len(set(keys))


def test_copy_catalog_required_keys_exist() -> None:
    for key in REQUIRED_KEYS:
        assert copy_text(key)
